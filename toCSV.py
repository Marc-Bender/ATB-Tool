#! /bin/python3
#
import subprocess as sub
import os
import re
import sys

from datevCSV import datevBuchungszeileBuchungsstapelformat as buZeile

outputfile = ""
outputfilename = ""
inputfoldername = ""

dryRun = 1

def getContents(file,bz):
    file = open(file, "r")
    linesOfFile = file.readlines()
    for line in linesOfFile:
        matcherObj = re.compile("(.*)  \s*Kunden-Nr\.[^0-9]*([0-9]*).*").match(line)

        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
            bz.gegenkonto = matcherObj.group(2)
        else:
            pass
        matcherObj = re.compile("(.*)  \s*Rechnungs-Nr\.[^0-9]*([0-9]*).*").match(line)

        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
            bz.belegfeld1 = matcherObj.group(2)
        else:
            pass

        matcherObj = re.compile("(.*)  \s*Datum[^0-9.]*([0-9.]*).*").match(line)
        
        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
            bz.belegdatum = matcherObj.group(2)
            matcherObj = re.compile("([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{4})").match(bz.belegdatum)
            bz.belegdatum = matcherObj.group(1) + matcherObj.group(2)
        else:
            pass

        matcherObj = re.compile(".*Aufzugs-Nr\.[^0-9]*([0-9]*).*").match(line)

        if matcherObj:
            bz.belegfeld2 = matcherObj.group(1)
        else:
            pass

        matcherObj = re.compile("^ ([0-9]+ [A-Za-z.\- ]*$)").match(line)

        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
            break # already filled all the fields that are low hanging fruits
            # continue putting the file through the recogintion what is what
        else:
            pass
            

def main():
    if not (len(sys.argv) == 3):
        # incorrect parameter count
        print("Aufrufkonvention: toCSV.py Eingabeordner Ausgabedatei.csv")
        exit()
    else:
        #correct parameter count
        inputfoldername = sys.argv[1]
        outputfilename = sys.argv[2]
        if not os.path.isdir(inputfoldername):
            print("Eingangsverzeichnis nicht akzeptiert")
        else:
            if not dryRun == 1:
                os.system("ls *.pdf | xargs -IX pdftotext -layout X X.txt")
            else:
                print("Tun wir mal als wie wenn schon konvertiert sei")
            txtfilelist = []
            sp = sub.Popen(['ls'],stdout=sub.PIPE)
            output, _ = sp.communicate()
            output = str(output).replace('\\n',';')
            output = re.split(";", output)
            for element in output:
                if str(element).__contains__(".pdf.txt"):
                    txtfilelist.append(element)
                else:
                    pass
            outputfile = open(outputfilename, "w+")

            for file in txtfilelist:
                bz = buZeile()
                getContents(file,bz)
                
                outputfile.write(re.sub(" +"," ",bz.toCSV_String()) + "\n")

main() # call main at start of programm

