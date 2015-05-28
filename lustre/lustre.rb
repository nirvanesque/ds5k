#
# Author:: Mehrez Alachheb (<mehrez.alachheb@inria.fr>)
#

require 'net/sftp'

module Dfs5k
  class Lustre < Dfs5k::Dfs
    attr_reader :mdt
    attr_reader :ost
    attr_reader :mgs
    attr_reader :clt
    attr_reader :config

    def initialize()
      @master = Hash.new
      @dataNodes = Array.new
      @clients = Array.new
    end

    def parse_conf(conf_file)
      conf = YAML.load_file(conf_file)
      @name = conf["name"]
      @options= conf["options"]
      @dataDir = conf["dataDir"]
      @master["user"] = conf["master"].split("@")[0]
      @master["host"] = conf["master"].split("@")[1]
      @master["addr"] = IPSocket.getaddress(@master["host"])
      conf["dataNodes"].split.each_with_index do |node, index|
        @dataNodes[index] = Hash.new
        @dataNodes[index]["user"] = node.split("@")[0]
        @dataNodes[index]["host"] = node.split("@")[1]
      end
      conf["clients"].split.each_with_index do |node, index|
        @clients[index] = Hash.new
        @clients[index]["user"] = node.split("@")[0]
        @clients[index]["host"] = node.split("@")[1]
      end
    end
    
    def deploy
      # Create the meta data server 
      puts "Initializing the MDT server: #{@master["host"]}, this operation can take a time ..."
      self.init_mdt_server
      # Create the object data server
      @dataNodes.each do |dataNode|
        puts "Initializing the OST server #{dataNode["host"]}, this operation can take a time ..."
        self.init_ost_server(dataNode['host'], dataNode['user'])
      end
    end

    def undeploy
      puts "The undeploying lustre file system"
      puts "Cleaning the MDT server: #{@master['host']}:"
      clean_mdt_server
      @dataNodes.each do |dataNode|
        puts "Cleaning the lustre storage servers #{dataNode['host']}"
        clean_ost_server(dataNode['host'], dataNode['user'])
      end
      
    end


    def check(nodes_file)
      self.init_servers(nodes_file)
      puts "mdt server (#{@master['host']}) status: #{self.check_server_health(@master['host'],@master['user'])}"
      @dataNodes.each do |dataNode|
        puts "ost server (#{dataNode['host']}) status: #{self.check_server_health(dataNode['host'], dataNode['user'])}"
      end
    end

    def clean_mdt_server
      msg = "Failed to cleaning the lustre metadata server #{@master['host']}"
      host = @master['host']
      user = @master['user']
      Helpers::exec_with_exception(host, user, msg) {
        External.ssh_cmd("umount /mnt/mdt", host, user) if Helpers::check_remote_mount("/mnt/mdt", host, user)
        External.ssh_cmd("umount /tmp", host, user) if Helpers::check_remote_mount("/tmp", host, user)
        External.ssh_cmd("mkfs.ext3  -m 0 -E lazy_itable_init=1 -O uninit_bg /dev/sda5", host, user)
        External.ssh_cmd("mount /dev/sda5 /tmp", host, user)
      }
    end

    def clean_ost_server(host, user)
      msg = "Failed to Cleaning the lustre  storage server in node #{host}"
      Helpers::exec_with_exception(host, user, msg) {
        External.ssh_cmd("umount /mnt/ost", host, user) if Helpers::check_remote_mount("/mnt/ost", host, user)
        External.ssh_cmd("umount /tmp", host, user) if Helpers::check_remote_mount("/tmp", host, user)
        External.ssh_cmd("mkfs.ext3 -m 0 -E lazy_itable_init=1 -O uninit_bg /dev/sda5", host, user)
        External.ssh_cmd("mount /dev/sda5 /tmp", host, user)
      }
    end
    
    def check_server_health(host, user)
      Net::SFTP.start(host, user) do |sftp|
        sftp.file.open("/proc/fs/lustre/health_check", "r") do |f|
          line = f.gets
          return line
        end
      end
    end

    def init_mdt_server
      msg = "Failed to initialize the MDT server in node #{@master["host"]}"
      Helpers::exec_with_exception(@master["host"], @master["user"], msg) {
        External.ssh_cmd("umount /tmp", @master["host"], @master["user"]) if Helpers::check_remote_mount("/tmp", @master["host"], @master["user"])
        External.ssh_cmd("mkdir -p /mnt/mdt", @master["host"], @master["user"])
        External.ssh_cmd("mkfs.lustre --fsname #{@name} --mdt --mgs /dev/sda5", @master["host"], @master["user"])
        External.ssh_cmd("mount -t lustre /dev/sda5 /mnt/mdt", @master["host"], @master["user"])
      }
    end
      
    def init_ost_server(host, user)
      msg = "Failed to create th OST server in node #{host}"
      Helpers::exec_with_exception(host, user, msg) {
        External.ssh_cmd("umount /tmp", host, user) if Helpers::check_remote_mount("/tmp", host, user)
        External.ssh_cmd("mkdir -p /mnt/ost", host, user)
        External.ssh_cmd("mkfs.lustre --fsname #{@name} --ost --mgsnode=#{@master["addr"]}@tcp0 /dev/sda5", host, user)
        External.ssh_cmd("mount -t lustre /dev/sda5 /mnt/ost", host, user)
      }
    end
    
    def mount(action)
      mount_cmd = "mount -t lustre #{@master['addr']}:/#{@name} /dfs"
      Helpers::mount(action, @clients, @user ,mount_cmd, "Lustre")
    end
                    
  end
end
