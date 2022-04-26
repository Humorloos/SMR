# import required modules

import os
import zipfile


# Declare the function to return all file paths of the particular directory
def retrieve_file_paths(dirName):
    # setup file paths variable
    filePaths = []
    directories_2_exclude = {
        '.git',
        'tests',
        '__pycache__',
        '.idea',
        'icons',
        'resources',
        'screenshots',
    }
    files_2_exlude = {
        '.gitignore',
        'CHANGELOG.md',
        'content.xml',
        'license.txt',
        'README.md',
        'requirements.txt',
        'requirements2.txt',
        'zipYourself.py',
    }
    # Read all directory, subdirectories and file lists
    for root, directories, files in os.walk(dirName):
        directories[:] = [d for d in directories if d not in directories_2_exclude]
        for filename in files:
            if not (filename in files_2_exlude):
                # Create the full filepath by using os module.
                filePath = os.path.join(root, filename)
                filePaths.append(filePath)

    # return all paths
    return filePaths


# Declare the main function
def main():
    # Assign the name of the directory to zip
    dir_name = os.getcwd()

    # Call the function to retrieve all files and folders of the assigned directory
    filePaths = retrieve_file_paths(dir_name)

    # printing the list of all files to be zipped
    print('The following list of files will be zipped:')
    for fileName in filePaths:
        print(fileName)

    # writing files to a zipfile
    zip_file = zipfile.ZipFile(file=dir_name + '.ankiaddon', mode='w')
    with zip_file:
        # writing each file one by one
        for file in filePaths:
            zip_file.write(filename=file, arcname=file[len(dir_name):])

    print(dir_name + '.zip file is created successfully!')


# Call the main function
if __name__ == "__main__":
    main()
