"""Build official hnswlib locally using an existing MinGW compiler on Windows.

No setup.py execution, global installs, or system compiler installation. Sources
are downloaded from official PyPI metadata and their SHA-256 digests verified.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,sysconfig,tarfile,urllib.request,zipfile

ROOT=Path(__file__).resolve().parents[2]

def artifact(project,kind,version,expected_sha):
    with urllib.request.urlopen(f'https://pypi.org/pypi/{project}/{version}/json',timeout=60) as response: data=json.load(response)
    choices=[file for file in data['urls'] if file['packagetype']==kind]
    if kind=='bdist_wheel': choices=[file for file in choices if file['filename'].endswith('py3-none-any.whl')]
    file=choices[0]
    if file['digests']['sha256']!=expected_sha: raise ValueError('official metadata differs from pinned checksum')
    directory=ROOT/'.smriti'/'deps'; directory.mkdir(parents=True,exist_ok=True)
    destination=directory/file['filename']
    if not destination.exists():
        with urllib.request.urlopen(file['url'],timeout=120) as response: destination.write_bytes(response.read())
    if hashlib.sha256(destination.read_bytes()).hexdigest()!=file['digests']['sha256']: raise ValueError('artifact checksum mismatch')
    return destination,{'project':project,'version':data['info']['version'],'filename':file['filename'],'url':file['url'],'sha256':file['digests']['sha256']}

def build():
    compiler=shutil.which('g++')
    if compiler is None: raise RuntimeError('existing MinGW g++ required')
    source,source_meta=artifact('hnswlib','sdist','0.8.0','cb6d037eedebb34a7134e7dc78966441dfd04c9cf5ee93911be911ced951c44c')
    headers,headers_meta=artifact('pybind11','bdist_wheel','3.1.0','b8488090f8acffbcb6b5d6a85571a6827a0a2981ffb75e5a0b27b87c4a6b7dd0')
    directory=ROOT/'.smriti'/'deps'; unpacked=directory/'source'; unpacked.mkdir(exist_ok=True)
    with tarfile.open(source) as archive: archive.extractall(unpacked,filter='data')
    include=directory/'pybind11-headers'
    with zipfile.ZipFile(headers) as archive:
        for name in archive.namelist():
            if not name.startswith('pybind11/include/') or name.endswith('/'): continue
            target=(include/name).resolve()
            if not target.is_relative_to(include.resolve()): raise ValueError('unsafe header path')
            target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(archive.read(name))
    package=next(unpacked.glob('hnswlib-*'))
    output=directory/('hnswlib'+sysconfig.get_config_var('EXT_SUFFIX'))
    python_lib=Path(sys.base_prefix)/'libs'/f'python{sys.version_info.major}{sys.version_info.minor}.lib'
    command=[compiler,'-O3','-shared','-std=c++17','-static-libgcc','-static-libstdc++',f'-I{sysconfig.get_path("include")}',f'-I{include/"pybind11"/"include"}',f'-I{package/"hnswlib"}',str(package/'python_bindings'/'bindings.cpp'),str(python_lib),'-o',str(output)]
    result=subprocess.run(command,text=True,capture_output=True,timeout=300)
    manifest={'source':source_meta,'headers':headers_meta,'compiler':compiler,'command':command,'returncode':result.returncode,'stderr':result.stderr,'output':str(output)}
    (directory/'reference_build.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if result.returncode: raise RuntimeError(result.stderr)
    manifest['binary_sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    manifest['compiler_version']=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]
    (directory/'reference_build.json').write_text(json.dumps(manifest,indent=2)+'\n')
    sys.path.insert(0,str(directory))
    with os.add_dll_directory(str(Path(compiler).parent)):
        import hnswlib
        index=hnswlib.Index(space='cosine',dim=2); index.init_index(max_elements=2); index.add_items([[1.,0.],[0.,1.]],[0,1]); assert index.knn_query([[1.,0.]],k=1)[0][0][0]==0
    return manifest

if __name__=='__main__': print(json.dumps(build(),indent=2))
