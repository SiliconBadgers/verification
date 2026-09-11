import argparse
from pathlib import Path
import shutil
import subprocess

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rtl-root',type=Path,required=True)
    p.add_argument('--vectors',type=Path,required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parent
    for tool in ['iverilog','vvp']:
        if not shutil.which(tool): p.error(f'Missing {tool}; install Icarus Verilog')
    rtl=a.rtl_root.resolve()/'rtl/pe_mac.sv'
    vectors=a.vectors.resolve()
    if not rtl.is_file() or not vectors.is_file(): p.error('Missing RTL or vector input')
    build=root/'build'
    build.mkdir(exist_ok=True)
    image=build/'mac.vvp'
    subprocess.run(['iverilog','-g2012','-s','pe_mac_smoke_tb','-o',str(image),str(rtl),str(root/'tb/pe_mac_smoke_tb.sv')],check=True,timeout=60)
    result=subprocess.run(['vvp',str(image),f'+VECTORS={vectors}'],capture_output=True,text=True,timeout=120)
    print(result.stdout,end='')
    if result.stderr: print(result.stderr,end='')
    if result.returncode or 'PASS golden vectors checked=' not in result.stdout or 'PASS pe_mac_smoke' not in result.stdout:
        raise SystemExit('FAIL cross-repository MAC verification')

if __name__=='__main__': main()
