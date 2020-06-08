import argparse
import json
import os
import re
import sys
import subprocess
import tempfile

def get_c3(url, tenant, tag, mode='thick', define_types=True, auth=None):
    """
    Returns c3remote type system for python.
    """
    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen
    from types import ModuleType
    c3iot = ModuleType('c3IoT')
    c3iot.__loader__ = c3iot
    src = urlopen(url + '/public/python/c3remote_bootstrap.py').read()
    exec(src, c3iot.__dict__)
    return c3iot.C3RemoteLoader.typeSys(
        url=url,
        tenant=tenant,
        tag=tag,
        mode=mode,
        auth=auth,
        define_types=define_types
    )

def provision_environment(temp_reqfile, runtime_prefix):
    try:   
        # provision initial conda environment
        conda_command = ['conda', 'env', 'create', '-p', runtime_prefix, '--file', temp_reqfile.name]
        print(' '.join(conda_command))
        subprocess.check_call(conda_command)

        print("Environment {} has been provisioned!".format(runtime_prefix))
    except:
        raise RuntimeError("Environment {} failed to be provisioned!".format(runtime_prefix))

parser = argparse.ArgumentParser('Provision an action runtime')
parser.add_argument('--package', help="Directory containing the c3 package", type=str)
parser.add_argument('--server', help="Vanity url of running c3 server to connect to", type=str)
parser.add_argument('--tenant', help="Tenant to connect to", type=str)
parser.add_argument('--tag', help='Tag to connect to', type=str)
parser.add_argument('--list', help="List available action runtimes", action='store_true')
parser.add_argument('--runtime', help="Provision this runtime", type=str)
parser.add_argument('--runtime-prefix', help="The prefix to store the runtime at", type=str)

args = parser.parse_args()

# Two paths
if args.package is None and args.server is None:
    raise RuntimeError("Please specify either --package or --server")

if args.package is not None and args.server is not None:
    raise RuntimeError("Please specify only one of --package or --server")

if args.package is not None:

    package_path = args.package

    if not os.path.exists(package_path):
        raise RuntimeError("Path {} doesn't exist.".format(package_path))
    
    action_runtime_path = 'seed/ActionRuntime'
    action_runtime_dir = '/'.join([package_path, action_runtime_path])
    
    # Get list of available action_runtimes
    action_runtime_list = os.listdir(action_runtime_dir)
    
    json_file_re = re.compile('.*\.json$')
    def is_json_file(filename):
        return json_file_re.match(filename) is not None
    
    def get_runtime_name(filename):
        return '.'.join(filename.split('.')[:-1])
    
    action_runtime_list = list(map(get_runtime_name, filter(is_json_file, action_runtime_list)))
    
    if args.list:
        for f in action_runtime_list:
            print(f)
        sys.exit(0)
    
    runtime = args.runtime
    if runtime is None:
        raise RuntimeError("Please specify a runtime, or list!")
    
    if runtime not in action_runtime_list:
        raise RuntimeError("Runtime {} not available!".format(runtime))
    
    # Build runtime prefix path
    runtime_prefix = args.runtime_prefix
    if runtime_prefix is None:
        runtime_prefix = runtime+"_venv"
    
    # Check whether runtime prefix exists
    if os.path.exists(runtime_prefix):
        raise RuntimeError("runtime_prefix {} already exists!".format(runtime_prefix))
    
    # Read in runtime json file
    runtime_json = json.loads(open('/'.join([action_runtime_dir,'.'.join([runtime, 'json'])]),'r').read())
    
    # Get list of conda and pip package specifications
    conda_packages = []
    pip_packages = []
    conda_re = re.compile('^conda\..*')
    pip_re = re.compile('^pip\..*')
    for key in runtime_json['modules']:
        if conda_re.match(key) is not None:
            conda_packages.append(key[6:]+runtime_json['modules'][key])
        if pip_re.match(key) is not None:
            pip_packages.append(key[4:]+runtime_json['modules'][key])
    
    python_version = runtime_json['runtimeVersion']
    
    # Create temporary named file for requirements.yaml
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as temp_reqfile:
        temp_reqfile.writelines(['#conda env create --file requirements.yaml\n'])
    
        # name
        temp_reqfile.writelines(['name: {}\n'.format(runtime)])
    
        # channels
        temp_reqfile.writelines(['channels:\n'])
    
        # Repos
        for repo in runtime_json['repositories']:
            if 'c3-e' not in repo:
                temp_reqfile.writelines(['- '+repo+'\n'])
    
        # dependencies
        temp_reqfile.writelines(['dependencies:\n'])
    
        # conda packages
        for package in conda_packages:
            temp_reqfile.writelines(['- '+package+'\n'])
    
        # Write python version
        temp_reqfile.writelines(['- python='+python_version+'\n'])
    
        # pip packages
        if len(pip_packages) > 0:
            temp_reqfile.writelines([
                '- pip\n',
                '- pip:\n',
            ])
            for package in pip_packages:
                temp_reqfile.writelines(['  - '+package+'\n'])
    
        temp_reqfile.flush()
    
        provision_environment(temp_reqfile, runtime_prefix)

else:
    # Handle connecting to a running c3 session
    if args.tenant is None:
        raise RuntimeError("Please specify the tenant with --tenant if using --server mode.")
    if args.tag is None:
        raise RuntimeError("Please specify the tag with --tag if using --server mode.")

    c3 = get_c3(args.server, args.tenant, args.tag)
    python_envs = c3.CondaActionRuntime.requirementsFilesForLanguage('Python')

    if args.list:
        for f in python_envs.keys():
            print(f)
        sys.exit(0)

    runtime = args.runtime
    if runtime is None:
        raise RuntimeError("Please specify a runtime, or list!")
    
    if runtime not in python_envs.keys():
        raise RuntimeError("Runtime {} not available!".format(runtime))

    # Build runtime prefix path
    runtime_prefix = args.runtime_prefix
    if runtime_prefix is None:
        runtime_prefix = runtime+"_venv"

    tempfile_text = python_envs[runtime]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as temp_reqfile:
        temp_reqfile.write(tempfile_text)
        temp_reqfile.flush()

        provision_environment(temp_reqfile, runtime_prefix)
