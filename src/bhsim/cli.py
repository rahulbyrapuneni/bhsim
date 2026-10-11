import argparse
import json
from .engine import Config, generate, validate, export_csv

def main():
    parser=argparse.ArgumentParser(description='BHSim synthetic behavioral health data generator')
    sub=parser.add_subparsers(dest='command',required=True)
    gen=sub.add_parser('generate')
    gen.add_argument('path')
    gen.add_argument('--clients',type=int,default=1000)
    gen.add_argument('--employees',type=int,default=80)
    gen.add_argument('--months',type=int,default=12)
    gen.add_argument('--future-days',type=int,default=30)
    gen.add_argument('--reference-date',default='2026-10-10')
    gen.add_argument('--seed',type=int,default=42)
    valid=sub.add_parser('validate');valid.add_argument('path')
    exp=sub.add_parser('export-csv');exp.add_argument('path');exp.add_argument('directory')
    a=parser.parse_args()
    if a.command=='generate':
        result=generate(a.path,Config(a.clients,a.employees,a.months,a.future_days,a.reference_date,a.seed))
    elif a.command=='validate':result=validate(a.path)
    else:result=export_csv(a.path,a.directory)
    print(json.dumps(result,indent=2))
    if a.command=='validate' and not result['valid']:raise SystemExit(1)

if __name__=='__main__': main()
