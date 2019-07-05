## How to use it.

Fork it, add your steps' scripts into `jobchain/step` folder.

## Step script

The script file name of step should not start with `_`, but you can put your common or useful functions into it.   

For each step script, there is a function named `run` that can accept the parameters defined in the configuration file 
and can return any value which will be temporarily saved for the following steps.

## Configuration

The configuration file format is `YAML`, 
the configuration file contains three parts, separately are `repositories`, `template` and `variable`.

* **repositories**   
It contains repositories, each repository contains jobs, each job contains ordered steps.  
This is an example:
```yaml
repositories:
  bamboo-framework:
    daily:
      checkout:
      maven:
        deploy_repository: releaseRspository::default::http://${nexus_user}:${nexus_password}@192.168.1.20:8080/nexus/content/repositories/snapshots
    start-release:
      checkout:
      start_release:
    update-release:
      checkout:
        branch: release/${release_version}
      update_release:
    finish-release:
      checkout:
      finish_release:
```
\* In the above example, defined a repository named `bamboo-framework`, and four jobs under it, separately named `daily`,
`start-release`, `update-release` and `finish-release`, each job contains ordered steps.  
\* About the step, its name is the same as the step script file name but without the extension, and the parameters are 
defined under it.  
\* In some cases, we have to use the same step more than once in a job, so allowed give the step a alias name to 
identify it. For example, the step `checkout` with a alias name `web` can be defined in format `checkout.web`.

* **template**  
Since allowed define multiple repositories and jobs, they will share the step definitions, if we already defined the 
step templates we can just reference them with the step name.  
In `repositories` section, if you reference a step (with alias) which has been defined in `template` section, will 
inherit the parameters and allowed you override them. 

* **variable**  
Allow define the variables that can be shared in steps, also you can override them by pass the command arguments with 
`-e` option. 

## Installation

```bash
pip install https://github.com/zhangyanwei/job-chain/archive/master.zip
```

## Command line

```bash
python -m jobchain -h
```
