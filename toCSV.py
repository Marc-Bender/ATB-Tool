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

class elementLine:
    positionNr: str = ""
    elementText: str = ""
    quantity: str = ""
    unitPrice: str = ""
    elementTotal: str = ""
    def __init__(self):
        positionNr = ""
        elementText = ""
        quantity = ""
        unitPrice = ""
        elementTotal = ""

def handleElementLine(elementLineObj, bz):
    returnValue = [bz]
    iterator = 0
    if elementLine.elementTotal.__contains__("-"):
        #negative number --> haben
        returnValue[iterator].sollHabenKZ = "H"
    else:
        returnValue[iterator].sollHabenKZ = "S"
    if elementLine.elementText.__contains__("Reparatur an o.g. Aufzugsanlage"):
        # element is for repairs
        returnValue[iterator].gegenkonto = "8403"
        # filling the prices is not yet implemented
    elif elementLine.elementText.__contains__("Notrufvertrag"):
        returnValue[iterator].gegenkonto = "8402" # TODO: check if correct (duplicate entry in table)
        #check if current year or previous year
        matcherObj = re.compile(".*Vertragsjahr ([0-9]{4}).*").match(elementLine.elementText)
        returnValue[iterator].umsatz = elementLine.elementTotal # for the inial line full price, then if current year inject partial lines with negative (ie inverted S/H)
        if (
                    (matcherObj)
                and (returnValue[iterator].belegdatum.__contains__(matcherObj.group(1)))
           ):
            # current year, thus inject bz object
            
            iterator += 1
            returnValue.append(bz)
            if not (elementLine.quantity == 1):
                # price is already given in smaller unit --> take that price for partial revokation
                returnValue[iterator].umsatz = Decimal(float(elementLine.unitPrice.replace(",","."))).quantize(Decimal("0.01")) * (Decimal(float(elementLine.quantity)) - Decimal(1))
                returnValue[iterator].umsatz = str(float(returnValue[iterator]))
            else:
                # price is given in one total for the entire year
                returnValue[iterator].umsatz = Decimal(float(elementLine.unitPrice.replace(",","."))/12*11).quantize(Decimal("0.01"))
            if returnValue[iterator - 1].sollHabenKZ == "S":
                returnValue[iterator].sollHabenKZ = "H"
            else:
                returnValue[iterator].sollHabenKZ = "S"
        elif (
                    (matcherObj)
                and not(returnValue[iterator].belegdatum.__contains__(matcherObj.group(1)))
             ):
            # previous year
            returnValue[iterator].gegenkonto = "9999" # dummy for previous year overhang stuff
    elif elementLine.elementText.__contains__("Wartung der Anlagen"):
        # element is for maintainance
        returnValue[iterator].gegenkonto = "8404"
        matcherObj = re.compile(".*Wartungsjahr ([0-9]{4}).*").match(elementLine.elementText)
        returnValue[iterator].umsatz = elementLine.elementTotal # for the inial line full price, then if current year inject partial lines with negative (ie inverted S/H)
        if (
                    (matcherObj)
                and (returnValue[iterator].belegdatum.__contains__(matcherObj.group(1)))
           ):
            # current year, thus inject bz object
            
            iterator += 1
            returnValue.append(bz)
            if not (elementLine.quantity == 1):
                # price is already given in smaller unit --> take that price for partial revokation
                returnValue[iterator].umsatz = Decimal(float(elementLine.unitPrice.replace(",","."))).quantize(Decimal("0.01")) * (Decimal(float(elementLine.quantity)) - Decimal(1))
                returnValue[iterator].umsatz = str(float(returnValue[iterator]))
            else:
                # price is given in one total for the entire year
                returnValue[iterator].umsatz = Decimal(float(elementLine.unitPrice.replace(",","."))/12*11).quantize(Decimal("0.01"))
            if returnValue[iterator - 1].sollHabenKZ == "S":
                returnValue[iterator].sollHabenKZ = "H"
            else:
                returnValue[iterator].sollHabenKZ = "S"
            if returnValue[iterator - 1].sollHabenKZ == "S":
                returnValue[iterator].sollHabenKZ = "H"
            else:
                returnValue[iterator].sollHabenKZ = "S"
        elif (
                    (matcherObj)
                and not(returnValue[iterator].belegdatum.__contains__(matcherObj.group(1)))
             ):
            # previous year
            returnValue[iterator].gegenkonto = "8888" # dummy for previous year overhang stuff

def getSpecialInformation(file,bz):
    returnValue = [bz]
    iterator = 0
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
                        returnValue[iterator].umsatz = matcherObj.group(1).replace(".","") # get total price and remove thousends deliminator
                        returnValue[iterator].gegenkonto = "8337" 
                        return returnValue, iterator # bz object is already filled --> function can terminate to allow writing the bz object to output file and continue with next file
                    else:
                        print("Dateiformatfehler in Datei " + file)
                        return [],0
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
            elementLineObj = elementLine()
            if matcherObj:
                # table end found; but the handling of the element line(s) has not been done for the last element thus handle the element line then exit the loop, but then there is nothing to do anymore thus return from the function
                handleElementLine(elementLine, returnValue[iterator]);
                return returnValue, iterator
            else:
                # table end not found check for various special cases
                # check for initial line of multiline position first
                matcherObj = re.compile("^\s*([0-9]+)\s*([0-9]+)\s*(.*)  \s*([0-9.]+,[0-9]{2})\s*([0-9.]+,[0-9]{2}).*$").match(linesOfFile[i])
                if (
                            (matcherObj)
                        and (initialLineMulitlinePosFound == 0)
                   ):
                    #found initial line of multiline position and it is the first line of that kind
                    #copy contents of that line in the elementLine element and keep walking through the table for remaining lines and elements
                    #the element line will be evaluated once either another elementline is found or the table end is reached
                    initialLineMulitlinePosFound = 1
                    elementLine.positionNr = matcherObj.group(1)
                    elementLine.quantity = matcherObj.group(2)
                    elementLine.elementText = matcherObj.group(3)
                    elementLine.matcherObj.group(4)
                    elementLine.elementTotal = matcherObj.group(5)
                elif initialLineMulitlinePosFound == 1:
                    #does not match initial line pattern and initialline is already found thus may be consecutive line or empty line
                    matcherObj = re.compile("\s*[^\s]+\s*").match(linesOfFile[i])
                    if matcherObj:
                        #non empty line --> append to elementText
                        elementLine.elementText += linesOfFile[i] # will add entire line but since line only consists of whitespace and the text that is no big deal. Whitespace sequences >2 will be removed after conversion to CSV string and before writing to the file.
                    else:
                        #empty line
                        pass
                elif (
                           (matcherObj)
                        and(initialLineMulitlinePosFound == 1)
                     ):

                    # initial line of multiline position but previous multiline position existed thus there needs to be special handling for writing the current bz object to the file and then creating a new one. 
                    # first store the contents of that line in seperate buffer
                    newElementLine = elementLine()
                    newElementLine.positionNr = matcherObj.group(1)
                    newElementLine.quantity = matcherObj.group(2)
                    newElementLine.elementText = matcherObj.group(3)
                    newElementLine.matcherObj.group(4)
                    newElementLine.elementTotal = matcherObj.group(5)
                    # then evaluate old elementLine
                    handleElementLine(elementLine, returnValue[iterator])
                    # increment the iterator so that when the new elementline is fully filled and either the end of the table is reached or the next element line is found the another bz object is generated in the returnValue array
                    iterator += 1
                    returnValue.append(bz) # add the bz object (that has not been modified since all actions are directly done in the return value object) to the returnValue to essentially copy the common "meta" information (like invoice no. etc)
                    # then replace old element line with new elementline and try to fill that to an end
                    elementLine = newElementLine
                else:
                    # first element line may also be incomplete as in repair invoices... 
                    # thus check for incomplete non empty line
                    matcherObj = re.compile("\s*[^\s]+\s*").match(linesOfFile[i])
                    if matcherObj:
                        #non empty line --> append to elementText, since element Text is empty by default there is no harm in doing so
                        elementLine.elementText += linesOfFile[i] # will add entire line but since line only consists of whitespace and the text that is no big deal. Whitespace sequences >2 will be removed after conversion to CSV string and before writing to the file.
                    else:
                        #empty line
                        pass

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

