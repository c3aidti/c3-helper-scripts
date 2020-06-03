import argparse
import json
import os
import re
import sys
import subprocess
import tempfile

parser = argparse.ArgumentParser('Provision an action runtime')
parser.add_argument('--package', help="Directory containing the c3 package", type=str, required=True)
parser.add_argument('--list', help="List available action runtimes", action='store_true')
parser.add_argument('--runtime', help="Provision this runtime", type=str)
parser.add_argument('--runtime-prefix', help="The prefix to store the runtime at", type=str)

args = parser.parse_args()

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

    try:   
        # provision initial conda environment
        conda_command = ['conda', 'env', 'create', '-p', runtime_prefix, '--file', temp_reqfile.name]
        print(' '.join(conda_command))
        subprocess.check_call(conda_command)

        print("Environment {} has been provisioned!".format(runtime_prefix))
    except:
        raise RuntimeError("Environment {} failed to be provisioned!".format(runtime_prefix))
