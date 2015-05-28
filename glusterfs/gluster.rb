#
# Author:: Mehrez Alachheb (<mehrez.alachheb@inria.fr>)
#
require 'dfs5k/dfs'


module Dfs5k
  class Gluster < Dfs5k::Dfs
    attr_reader :nodes

    def initialize()
      @dataNodes = Array.new
      @clients = Array.new
      @master = Hash.new
    end

    def version
      #External.cmd("gluster --version")
    end

    def start(node, user)
      Helpers::exec_with_exception(node, user, "Failed to start the File System") {
        External.ssh_cmd("/etc/init.d/glusterd restart", node, user)
      }
      end

    def stop(node, user)
      Helpers::exec_with_exception(node, user, "Failed to stop the File System") {
        External.ssh_cmd("/etc/init.d/glusterd stop", node, user)
      }
    end

    def parse_conf(conf_file)
      conf = YAML.load_file(conf_file)
      @name = conf["name"]
      @options= conf["options"]
      @master["user"] = conf["master"].split("@")[0]
      @master["host"] = conf["master"].split("@")[1]
      conf["dataNodes"].split.each_with_index do |node, index|
        @dataNodes[index] = Hash.new
        @dataNodes[index]["user"] = node.split("@")[0]
        @dataNodes[index]["host"] = node.split("@")[1].split(":")[0]
        @dataNodes[index]["space"] = node.split("@")[1].split(":")[1] 
      end
      conf["clients"].split.each_with_index do |node, index|
        @clients[index] = Hash.new
        @clients[index]["user"] = node.split("@")[0]
        @clients[index]["host"] = node.split("@")[1]
      end
    end
    
    def init_servers
      port = 24009
      $stdout.puts "Checking the nodes in  the configuration file..." 
      self.check_servers
      Helpers::exec_with_exception(@master["host"], @master["user"], "Failed to initializing) the master server") {
        self.start(@master["host"], @master["user"])
        External.ssh_cmd( "iptables -A INPUT  -m tcp -p tcp  -j ACCEPT", @master["host"], @master["user"])
        External.ssh_cmd( "iptables -A INPUT -m state --state NEW -m tcp -p tcp --dport 24008 -j ACCEPT", @master["host"], @master["user"])
        External.ssh_cmd( "iptables -A INPUT -m state --state NEW -m tcp -p tcp --dport 38465:38467 -j ACCEPT", @master["host"], @master["user"])
      }
       @dataNodes.each do |node|
        self.start(node["host"], node["user"])
        External.ssh_cmd( "iptables -A INPUT -m state --state NEW -m tcp -p tcp --dport #{port} -j ACCEPT", @master["host"], @master["user"])
        port = port + 1
      end
    end


    def deploy
      volume_server = ""
      @dataNodes.each do |node|
        puts "Adding #{node["host"]} to glusterfs storage servers"
        unless is_peer?(node['host'])
          External.ssh_cmd("/usr/sbin/gluster peer probe #{node["host"]}", @master["host"], @master["user"])
          volume_server = volume_server + " #{node["host"]}:#{node["space"]}"
        else
          $stdout.puts "host #{node['host']} already in peer list"
        end
      end
      puts "creation of glusterfs volume"
      unless self.exist?
        External.ssh_cmd("/usr/sbin/gluster volume create #{@name} #{@options} #{volume_server}", @master["host"], @master["user"])
      else
        $stdout.puts "Error: Volume #{@name} already exists"
      end

      puts "Starting the glusterfs volume"
      unless self.is_runing?
        External.ssh_cmd("/usr/sbin/gluster volume start #{@name}", @master["host"], @master["user"])
      else
        $stdout.puts "Volume #{@name} already started"
      end
      self.start(@master["host"], @master["user"])
    end


    def undeploy
      puts "Delete glusterfs volume"
     # Helpers::exec_with_exception(@master['host'], @master['user'], "Failed to undeploying Gluster file system") {
      if self.is_runing?
        External.ssh_cmd("yes | /usr/sbin/gluster volume stop #{@name}", @master["host"], @master["user"])
      else
        $stdout.puts "Error: Volume #{@name} is not in the started state"
      end
      
      if self.exist?
        External.ssh_cmd("yes | /usr/sbin/gluster volume delete #{@name}", @master["host"], @master["user"])
      else
        $stdout.puts "Error: Volume #{@name} does not exist"
      end
      
      @dataNodes.each do |node|
        puts "Detach #{node["host"]} from glusterfs storage servers"
        if is_peer?(node['host'])
          External.ssh_cmd("gluster peer detach #{node["host"]}", @master["host"], @master["user"])
          self.stop(node["host"], node["user"])
        else
          $stdout.puts "#{node['host']} is not part of cluster"
        end
      end
        #  }
      puts "Stoping the gluster file system '#{@name}'"
      self.stop(@master["host"], @master["user"])
    end


    def check_servers
      exit_status = 0
      # checking if gluster file system is installed
      unless  Helpers::check_remote_file("/usr/sbin/gluster", @master["host"], @master["user"])
        $stdout.puts "The gluster file system is not configured in the node master #{@master["host"]}"   
        exit_status = 1
      end
      @dataNodes.each do |node|
        unless  Helpers::check_remote_file("/usr/sbin/gluster", node["host"], node["user"])
          $stdout.puts "The gluster file system is not configured in the node #{node["host"]}"
          exit_status = 1
        end  
      end
      exit(exit_status) if exit_status == 1
    end

    def is_runing?
      return false unless self.exist?
      return Helpers::check_gluster_is_runing(@master["host"], @master["user"], @name)
    end

    def exist?
      unless Helpers::check_remote_file("/etc/glusterd/vols/#{@name}/info", @master["host"], @master["user"])
        return false
      else
        return true
      end
    end

    def is_peer?(node)
      cmd = "ssh #{@master["user"]}@#{@master["host"]} /usr/sbin/gluster peer status"
      peers = IO.popen(cmd)
      peers.readlines.each do |line|
        if line.include? "Hostname: #{node}"
          return true
        end
      end
      return false
      
    end
        

    # def master_undeploy(nodes_file)
    #   self.init_servers(nodes_file)
    #   puts "Stopping glusterfs volume"
    #   puts "Delete glusterfs volume"
    #   msg = "Failed to undeploying Gluster file system"
    #   Helpers::exec_with_exception(@master, @user, msg) {
    #     External.ssh_cmd("yes | gluster volume stop G5K_volume", @master, @user)
    #     External.ssh_cmd("yes | gluster volume delete G5K_volume", @master, @user)
    #     @servers.each do |node|
    #       puts "Detach #{node} from glusterfs storage servers"
    #       External.ssh_cmd("gluster peer detach #{node}", @master, @user)
    #     end
    #   }
    # end

    def mount(action)
      mount_cmd = "mount -t glusterfs #{@master["host"]}:/#{@name} /dfs"
      Helpers::mount(action, @clients, @user, mount_cmd, "Glusterfs")
    end

    
  end # class Gluster
end # module KadeployFS
