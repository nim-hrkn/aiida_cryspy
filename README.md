# aiida_cryspy
AiiDA interface to CrySPY

This is alpha version.

It is tested and runs only with aiida-lammps.

## Installation

### 1. Install CrysPy
Download CrysPy not from the original url, but from https://github.com/nim-hrkn/CrysPy, because many features are changed to fit AiiDA. Go to the downloaded directory, and
```shell
pip install . 
```
 or 
```shell
pip install -e .
```

### 2. Install aiida_cryspy

Download this package, and type
```shell
pip install . 
reentry scan
verdi daemon restart --reset
```
 or 
 ```shell
pip install -e .
reentry scan
verdi daemon restart --reset
```


## Examples

Sample scripts are in example/lammps_GaN_8_*/*.ipynb

## License

Apache



