# EAN-KOODI-GENERATOR

 > Click [here](https://rocksoft.atlassian.net/wiki/spaces/BAL/pages/832733185/EAN+koodi+generaator) to view the description of the initial task.
 

## Features

  * Generates EAN numbers in the range of EAN_NUMBER_START and EAN_NUMBER_END (both inclusive) in sequential order.
  * Assigns each unique AlternatePreparationCode with a newly generated EAN number.
    * If AlternatePreparationCode is 'None', the EAN number will not be generated and the event is logged as info.
  * Stores AlternatePreparationCodes and their corresponding EAN numbers in a local database. 
  * In the local database, cells of each column are configured to store unique values.
  * Updates Monitor database with EAN number as a value of ReferenceNumberDelivery for CustomerOrderRows.


## Technologies

Project is created with Python version 3.10.2


## Running the project

  1. Make sure you have the following files or folders in the same directory (default setting).
        * EAN-KOODI-GENERATOR-100.exe
        * config.ini
        * POINTER.txt
        * local_database.db
  2. The directory of local database can be configured in config.ini.
 

## Rebuilding the project

##### Install dependencies

> cd the directory to where requirements.txt is located, activate your virtualenv and make the installation.
```
pip install -r requirements.txt
```

##### Convert .py to .exe using [PyInstaller](https://pyinstaller.readthedocs.io/en/stable/)	

###### Install:
```
pip install pyinstaller
```
###### Run:
```
pyinstaller main.py --name EAN-KOODI-GENERATOR-100 --onefile --noupx
```