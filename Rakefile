
require File.dirname(__FILE__) + '/lib/dfs5k/version'

require 'rubygems'
require 'rake/gempackagetask'
require 'rake/rdoctask'

GEM = 'dfs5k'
GEM_VERSION = '1.1.4'

gemspec = Gem::Specification.new do |s|
  s.name = %q{dfs5k}
  s.version = "1.1.4"

  s.required_rubygems_version = Gem::Requirement.new(">= 0") if s.respond_to? :required_rubygems_version=
  s.authors = ["Mehrez Alachheb"]
  s.date = %q{2011-08-04}
  s.default_executable = %q{dfs5k}
  s.description = %q{Grid'5000 tool to autodeploy a distrubuted File sysytem.}
  s.email = %q{mehrez.alachheb@inria.fr}
  s.executables = ["dfs5k"]	
  s.extra_rdoc_files = ["README.rdoc"]
  s.files = ["README.rdoc","lib/dfs5k", "lib/dfs5k/external.rb", "lib/dfs5k/application", "lib/dfs5k/application/dfs5k.rb", "lib/dfs5k/application.rb", "lib/dfs5k/config.rb", "lib/dfs5k/exceptions.rb", "lib/dfs5k/helpers.rb", "lib/dfs5k/version.rb", "lib/dfs5k/dfs.rb", "lib/dfs5k/glusterfs", "lib/dfs5k/glusterfs/gluster.rb", "lib/dfs5k/ceph", "lib/dfs5k/ceph/ceph.rb", "lib/dfs5k/ceph/ceph.conf.erb", "lib/dfs5k/lustre", "lib/dfs5k/lustre/lustre.rb", "bin/dfs5k"]
  s.homepage = %q{https://www.grid5000.fr/mediawiki/index.php/dfs5k}
  s.require_paths = [["lib"]]
  s.rubygems_version = %q{1.8.1}
  s.summary = %q{Grid'5000 tool to deploy a distributed File system.}


  s.add_runtime_dependency(%q<mixlib-config>, [">= 1.1.0"])
  s.add_runtime_dependency(%q<mixlib-cli>, [">= 1.1.0"])
  s.add_dependency(%q<logger>)	
  s.add_dependency(%q<open4>, ["= 1.1.0"])
  s.add_dependency(%q<net-ssh>)
  s.add_dependency(%q<net-sftp>)
  s.add_runtime_dependency(%q<json>, [">= 1.4.6"])
end


Rake::GemPackageTask.new(gemspec) do |pkg|
  pkg.gem_spec = gemspec
end

desc "Generate a gemspec file"
task :gemspec do
  File.open("#{GEM}.gemspec", "w") do |file|
    file.puts gemspec.to_ruby
  end
end


desc "Publish in g5kgems repository"
task :publish => [:gemspec, :package] do
  sh "scp pkg/#{GEM}-#{GEM_VERSION}.gem git.grid5000.fr:/tmp"
  sh "ssh git.grid5000.fr sudo mv /tmp/#{GEM}-#{GEM_VERSION}.gem /var/www/gems.grid5000.fr/htdocs/gems"
  sh "ssh git.grid5000.fr sudo gem generate_index --directory /var/www/gems.grid5000.fr/htdocs/"
end

desc "install dfs5k on qualif for testing"
task :qualif => [:gemspec, :package] do
  sh "scp pkg/#{GEM}-#{GEM_VERSION}.gem fsophia.sophia.grid5000.fr:"
  sh "ssh fsophia.sophia.grid5000.fr sudo gem install --no-ri --no-rdoc dfs5k"
end

desc "install dfs5k on node for testing"
task :qualif_node => [:gemspec, :package] do
  sh "scp pkg/#{GEM}-#{GEM_VERSION}.gem root@helios-9.sophia.grid5000.fr:"
  sh "ssh root@helios-9.sophia.grid5000.fr sudo gem install --no-ri --no-rdoc dfs5k"
end

require 'spec/rake/spectask'
Spec::Rake::SpecTask.new(:spec) do |spec|
  spec.libs << 'lib' << 'spec'
  spec.spec_files = FileList['spec/**/*_spec.rb']
end
