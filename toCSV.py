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

def getSpecialInformation(file,bz):
    file = open(file, "r")
    linesOfFile = file.readlines()
    file.close()
    i = 0
    tableHeaderFound = 0
    tableEndFound = 0
    # check for 13b first
    for i in range(0,len(linesOfFile)):
        matcherObj = re.compile(".*Übergang der Steuerschuld nach .*").match(linesOfFile[i])
        if matcherObj:
            # is 13b, get total --> thus search for line with total
            for j in range(0,i): # total line will be above 13b line
                matcherObj = re.compile(".*Endbetrag EUR.*").match(linesOfFile[j])
                if matcherObj:
                    # found total line information needed is in next line down
                    matcherObj = re.compile("^.*([0-9\.],[0-9]{2})\s*$").match(linesOfFile[j+1])
                    if matcherObj:
                        # line matches
                        bz.umsatz = matcherObj.group(1).replace(".","") # get total price and remove thousends deliminator
                        bz.gegenkonto = "8337" 
                        return # bz object is already filled --> function can terminate to allow writing the bz object to output file and continue with next file
                    else:
                        print("Dateiformatfehler in Datei " + file)
                        return
                else:
                    # not found --> keep searching
                    pass
        else:
            # is not 13b search for and evaluate table with code segment below
            pass


    initialLineMulitlinePosFound = 0
    positionText = ""
    # get information from the table
    for i in range(0,len(linesOfFile)):
        if tableHeaderFound == 0:
            # table header not found seek to position of table
            matcherObj = re.compile("^.*Pos\..*Menge.* Einh\..*Artikelbezeichnung.*Einzelpreis.*Gesamtpreis.*$").match(linesOfFile[i])
            if matcherObj:
                tableHeaderFound = 1
            else:
                # continue searching
                pass
        else:
            # table header found but table end not reached --> do checks
            matcherObj = re.compile(".*^Bitte geben sie bei Zahlungen unbedingt die Rechnungsnummer an\..*$").match(linesOfFile[i])
            if matcherObj:
                # table end found --> end the loop
                break
            else:
                # table end not found check for various special cases
                # check for initial line of multiline position first
                matcherObj = re.compile("^\s*([0-9]+)\s*([0-9]+)\s*(.*)  \s*([0-9.]+,[0-9]{2})\s*([0-9.]+,[0-9]{2}.*$").match(linesOfFile[i])
                if (
                            (matcherObj)
                        and (initialLineMulitlinePosFound == 0)
                   ):
                    #found initial line of multiline position and it is the first line of that kind
                    initialLineMulitlinePosFound = 1
                    #positionNr = matcherObj.group(1)
                    #qty = matcherObj.group(2)
                    positionText = matcherObj.group(3)
                    #unitprice = matcherObj.group(4)
                    #positionTotal = matcherObj.group(5)
                else if initialLineMulitlinePosFound == 1:
                    #consecutive line in multiline position ?
                    matcherObj = re.compile("\s*[^\s]*\s*").match(linesOfFile[i])
                    if matcherObj:
                        #non empty line --> append to positionText
                        positionText += linesOfFile[i] # will add entire line but since line only consists of whitespace and the text that is no big deal. Whitespace sequences >2 will be removed after conversion to CSV string and before writing to the file.
                    else:
                        #empty line
                        pass
                else: 
                    # initial line of multiline position but previous multiline position existed thus there needs to be special handling for writing the current bz object to the file and then creating a new one. 
                    pass # dummy until feature is implemented

def cleanupDate(bz):
    matcherObj = re.compile("([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{4})").match(bz.belegdatum)
    bz.belegdatum = matcherObj.group(1) + matcherObj.group(2)

def getGeneralInformation(file,bz):
    file = open(file, "r")
    linesOfFile = file.readlines()
    file.close()
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
        else:
            pass

        matcherObj = re.compile(".*Aufzugs-Nr\.[^0-9A-Za-z]*([0-9A-Za-z]*).*").match(line)

        if matcherObj:
            bz.belegfeld2 = matcherObj.group(1)
        else:
            pass

        matcherObj = re.compile("^ ([0-9]+ [A-Za-z.\- ]*$)").match(line)

        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
        else:
            pass
            

        #check if all low hanging fruits are already picked up (ie. easy fields are filled)
        if (
                (not(bz.buchungstext == ""))
             and(not(bz.belegfeld1 == ""))
             and(not(bz.belegfeld2 == ""))
             and(not(bz.belegdatum == ""))
           ):
            break
        else:
            pass # continue gathering the information

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
                oldworkingDir = os.getcwd()
                os.chdir(inputfoldername)
                os.system("ls *.pdf | xargs -IX pdftotext -layout X X.txt")
                os.chdir(oldworkingDir)
            else:
                print("Tun wir mal als wie wenn schon konvertiert sei")
            txtfilelist = []
            os.chdir(inputfoldername)
            sp = sub.Popen(['ls'],stdout=sub.PIPE)
            output, _ = sp.communicate()
            output = str(output).replace('\\n',';').replace("b\'","")
            output = re.split(";", output)
            for element in output:
                if str(element).__contains__(".pdf.txt"):
                    txtfilelist.append(element)
                else:
                    pass
            outputfile = open(outputfilename, "w+")

            for file in txtfilelist:
                bz = buZeile()
                bz.beleginfoArt1 = "Kunden PDF Name"
                bz.beleginfoInhalt1 = str(file).replace(".txt", "")
                getGeneralInformation(file,bz)
                getSpecialInformation(file,bz)
                outputfile.write(re.sub(" +"," ",bz.toCSV_String()) + "\n")

main() # call main at start of programm

