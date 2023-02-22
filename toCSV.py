#! /bin/python3
#
import subprocess as sub
import os
import re
import sys
import platform

from datevCSV import datevBuchungszeileBuchungsstapelformat as buZeile
from elementLine import *

outputfile = ""
outputfilename = ""
inputfoldername = ""

dryRun = 1
debuggingActive = 1

regexNotrufvertragJahr = re.compile(".*Vertragsjahr ([0-9]{4}).*")
regexWartungsvertragJahr = re.compile(".*Wartungsjahr ([0-9]{4}).*")
regex13b = re.compile(".*Übergang der Steuerschuld nach .*")
regexEndbetrag = re.compile(".*Endbetrag EUR.*")
regexGesamtsumme = re.compile("^.*([0-9\.],[0-9]{2})\s*$")
regexElementLineFull = re.compile("^.*Pos\..*Menge.* Einh\..*Artikelbezeichnung.*Einzelpreis.*Gesamtpreis.*$")
regexEndOfTable = re.compile("^.*Bitte geben Sie bei Zahlungen unbedingt die Rechnungsnummer an\..*$")
regexInitialLine = re.compile("^\s*([0-9]+)\s*([0-9\,\. \-]+)\s*(.*)  \s*([0-9.]+,[0-9]{2})\s*([0-9\.\,\-]+,[0-9]{2}).*$")
regexElementLineTextOnly = re.compile("\s*[^\s]+\s*")
regexEmptyLine = re.compile("\s*[^\s]+\s*")
regexDateTTMMYYYY = re.compile("([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{4})")
regexKundennr = re.compile("(.*)  \s*Kunden-Nr\.[^0-9]*([0-9]*).*")
regexRechnungsnr = re.compile("(.*)  \s*Rechnungs-Nr\.[^0-9]*([0-9]*).*")
regexGutschriftsnr = re.compile("(.*)  \s*Gutschrifts-Nr\.[^0-9]*([0-9]*).*")
regexBelegdatum = re.compile("(.*)  \s*Datum[^0-9.]*([0-9.]*).*")
regexAufzugsnr = re.compile(".*Aufzugs-Nr\.[^0-9A-Za-z]*([0-9A-Za-z]*).*")
regexBuchungstext = re.compile("^ ([0-9]+ [A-Za-z.\- ]*$)")
isRepairString = "Reparatur"
isTUEVString = "TÜV - Hauptprüfung"

def handleElementLine(elementLineObj, bz):
    returnValue = [bz]
    iterator = 0
    elementLineObj.elementText = elementLineObj.elementText.replace("\n","")
    if elementLineObj.elementTotal.__contains__("-"):
        #negative number --> haben
        returnValue[iterator].sollHabenKZ = "H"
        elementLineObj.elementTotal = elementLineObj.elementTotal.replace("-","")
    else:
        returnValue[iterator].sollHabenKZ = "S"
    if elementLineObj.elementText.__contains__(isRepairString):
        # element is for repairs
        returnValue[iterator].konto = "8403"
        returnValue[iterator].umsatz = str(float(elementLineObj.elementTotal.replace(".","").replace(",",".")) * 1.19).replace(".",",")
    elif elementLineObj.elementText.__contains__("Notrufvertrag"):
        returnValue[iterator].konto = "8402" # TODO: check if correct (duplicate entry in table)
        #check if current year or previous year
        matcherObj = regexNotrufvertragJahr.match(elementLineObj.elementText.replace("\n",""))
        returnValue[iterator].umsatz = elementLineObj.elementTotal # for the inial line full price, then if current year inject partial lines with negative (ie inverted S/H)
        if (
                    (matcherObj)
                and (returnValue[iterator].belegdatum.__contains__(matcherObj.group(1)))
           ):
            # current year, thus inject bz object
            
            iterator += 1
            returnValue.append(bz)
            if not (elementLineObj.quantity == 1):
                # price is already given in smaller unit --> take that price for partial revokation
                returnValue[iterator].umsatz = str(float(elementLineObj.unitPrice.replace(".","").replace(",",".")) * (float(elementLineObj.quantity.replace(".","").replace(",",".")) - 1))
            else:
                # price is given in one total for the entire year
                returnValue[iterator].umsatz = str(float(elementLineObj.unitPrice.replace(".","").replace(",","."))*11/12)
            if returnValue[iterator - 1].sollHabenKZ == "S":
                returnValue[iterator].sollHabenKZ = "H"
            else:
                returnValue[iterator].sollHabenKZ = "S"
        elif (
                    (matcherObj)
                and not(returnValue[iterator].belegdatum.__contains__(matcherObj.group(1)))
             ):
            # previous year
            returnValue[iterator].konto = "9999" # dummy for previous year overhang stuff
    elif elementLineObj.elementText.__contains__("Wartung"):
        # element is for maintainance
        returnValue[iterator].konto = "8404"
        matcherObj = regexWartungsvertragJahr.match(elementLineObj.elementText.replace("",""))
        returnValue[iterator].umsatz = str(float(elementLineObj.elementTotal.replace(".","").replace(",",".")) * 1.19)  # for the inial line full price, then if current year inject partial lines with negative (ie inverted S/H)
        if (
                    (matcherObj)
                and (returnValue[iterator].belegdatum.__contains__(matcherObj.group(1)))
           ):
            # current year, thus inject bz object
            
            iterator += 1
            returnValue.append(bz)
            if not (elementLineObj.quantity == 1):
                # price is already given in smaller unit --> take that price for partial revokation
                returnValue[iterator].umsatz = str(float(elementLineObj.unitPrice.replace(".","").replace(",", ".")) * (float(elementLineObj.quantity.replace(".","").replace(",",".")) - 1) * 1.19)
            else:
                # price is given in one total for the entire year
                returnValue[iterator].umsatz = str(float(elementLineObj.unitPrice.replace(",","."))*1.19*11/12).replace(".",",")
            if returnValue[iterator - 1].sollHabenKZ == "S":
                returnValue[iterator].sollHabenKZ = "H"
            else:
                returnValue[iterator].sollHabenKZ = "S"
            if returnValue[iterator - 1].sollHabenKZ == "S":
                returnValue[iterator].sollHabenKZ = "H"
            else:
                returnValue[iterator].sollHabenKZ = "S"
        elif (
                    (
                            (matcherObj)
                        and not(returnValue[iterator].belegdatum.__contains__(matcherObj.group(1)))
                    )
                 or (
                        not (matcherObj)
                        and not(elementLineObj.elementText.__contains__(returnValue[iterator].belegdatum.rsplit(".")[0]))
                    )
             ):
            # previous year
            returnValue[iterator].konto = "8888" # dummy for previous year overhang stuff
            returnValue[iterator].umsatz = str(float(elementLineObj.elementTotal.replace(".","").replace(",",".")) * 1.19).replace(".",",")
    elif (elementLineObj.elementText.__contains__(isTUEVString)):
        returnValue[iterator].konto = "8406"
        returnValue[iterator].umsatz = str(float(elementLineObj.elementTotal.replace(".","").replace(",",".")) * 1.19).replace(".",",")
    else:
        returnValue[iterator].konto = "8400"
        returnValue[iterator].umsatz = str(float(elementLineObj.elementTotal.replace(".","").replace(",",".")) * 1.19).replace(".",",")

    return [returnValue, iterator]

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
        matcherObj = regex13b.match(linesOfFile[i])
        if matcherObj:
            # is 13b, get total --> thus search for line with total
            for j in range(0,i): # total line will be above 13b line
                matcherObj = regexEndbetrag.match(linesOfFile[j])
                if matcherObj:
                    # found total line information needed is in next line down
                    matcherObj = regexGesamtsumme.match(linesOfFile[j+1])
                    if matcherObj:
                        # line matches
                        returnValue[iterator].umsatz = matcherObj.group(1).replace(".","") # get total price and remove thousends deliminator
                        returnValue[iterator].konto = "8337" 
                        iterator += 1
                        return returnValue, iterator; # bz object is already filled --> function can terminate to allow writing the bz object to output file and continue with next file
                    else:
                        print("Dateiformatfehler in Datei " + file)
                        return [["Fehler"],0];
                else:
                    # not found --> keep searching
                    pass
        else:
            # is not 13b search for and evaluate table with code segment below
            pass

    initialLineMultilinePosFound = 0
    positionText = ""
    elementLineObj = elementLine()
    startsWithTextOnlyLine = 0
    # get information from the table
    for i in range(0,len(linesOfFile)):
        if tableHeaderFound == 0:
            # table header not found seek to position of table
            matcherObj = regexElementLineFull.match(linesOfFile[i])
            if matcherObj:
                tableHeaderFound = 1
            else:
                # continue searching
                pass
        else:
            # table header found but table end not reached --> do checks
            matcherObj = regexEndOfTable.match(linesOfFile[i])
            if matcherObj:
                # table end found; but the handling of the element line(s) has not been done for the last element thus handle the element line then exit the loop, but then there is nothing to do anymore thus return from the function
                returnValueElementLine, iteratorElementLine = handleElementLine(elementLineObj, returnValue[iterator]);
                if iteratorElementLine > 0:
                    # function has added another line to the datastructure
                    # special case when iterator == 1 will be handled correctly by this too
                    returnValue.pop() #.pop the last line since it will be the first line in the returnvalueElementLine Object
                    for value in returnValueElementLine:
                        returnValue.append(value) # will add the previously deleted line (populated with more values) + all the lines that were generated on top of that
                else: # iteratorElementLine == 0: 
                    # fault occured --> think of how to handle the file format errror
                    pass # dummy
                return [returnValue, iterator + 1];
            else:
                # table end not found check for various special cases
                # check for initial line of multiline position first
                matcherObj = regexInitialLine.match(linesOfFile[i])
                if (
                           (matcherObj)
                        and(startsWithTextOnlyLine == 1)
                   ):
                    # full line but repair invoice (section) detected : add elementTotals until new type of invoice (section) is detected
                    elementLineObj.elementTotal = float(elementLineObj.elementTotal.replace(".", "").replace(",","."))
                    secondSummand = matcherObj.group(5).replace(".","").replace(",",".")
                    secondSummand = float(secondSummand)
                    elementLineObj.elementTotal = elementLineObj.elementTotal + secondSummand
                    elementLineObj.elementTotal = str(elementLineObj.elementTotal).replace(".",",")
                elif (
                            (matcherObj)
                        and (initialLineMultilinePosFound == 0)
                     ):
                    #found initial line of multiline position and it is the first line of that kind
                    #copy contents of that line in the elementLine element and keep walking through the table for remaining lines and elements
                    #the element line will be evaluated once either another elementline is found or the table end is reached
                    initialLineMultilinePosFound = 1
                    elementLineObj.positionNr = matcherObj.group(1)
                    elementLineObj.quantity = matcherObj.group(2)
                    elementLineObj.elementText = matcherObj.group(3)
                    elementLineObj.unitPrice = matcherObj.group(4)
                    elementLineObj.elementTotal = matcherObj.group(5)
                elif(
                        not(matcherObj)
                        and(initialLineMultilinePosFound == 0)
                        and(startsWithTextOnlyLine == 0)
                        and(regexElementLineTextOnly.match(linesOfFile[i]))
                        and(
                                  (linesOfFile[i].__contains__(isRepairString))
                                or(linesOfFile[i].__contains__(isTUEVString))
                                or(linesOfFile[i].__contains__("Wartung"))
                           )
                    ):
                    # repair invoice starts out with text only line in table
                    startsWithTextOnlyLine = 1
                    elementLineObj.elementText += linesOfFile[i] 
                    elementLineObj.elementTotal = "0,00"
                elif (
                           (matcherObj)
                        and(initialLineMultilinePosFound == 1)
                        and(startsWithTextOnlyLine == 0)
                     ):

                    # initial line of multiline position but previous multiline position existed thus there needs to be special handling for writing the current bz object to the file and then creating a new one. 
                    # first store the contents of that line in seperate buffer
                    newElementLine = elementLine()
                    newElementLine.positionNr = matcherObj.group(1)
                    newElementLine.quantity = matcherObj.group(2)
                    newElementLine.elementText = matcherObj.group(3)
                    newElementLine.unitPrice = matcherObj.group(4)
                    newElementLine.elementTotal = matcherObj.group(5)
                    # then evaluate old elementLine
                    returnValueElementLine, iteratorElementLine = handleElementLine(elementLineObj, returnValue[iterator])
                    for element in returnValueElementLine:
                        #this will lead to duplicate entries in the returnValue object think this through better
                        returnValue.append(element)
                    # increment the iterator so that when the new elementline is fully filled and either the end of the table is reached or the next element line is found the another bz object is generated in the returnValue array
                    iterator += 1
                    returnValue.append(bz) # add the bz object (that has not been modified since all actions are directly done in the return value object) to the returnValue to essentially copy the common "meta" information (like invoice no. etc)
                    # then replace old element line with new elementline and try to fill that to an end
                    elementLineObj = newElementLine
                elif initialLineMultilinePosFound == 1:
                    #does not match initial line pattern and initialline is already found thus may be consecutive line or empty line
                    matcherObj = regexElementLineTextOnly.match(linesOfFile[i])
                    if matcherObj:
                        #non empty line --> append to elementText
                        elementLineObj.elementText += linesOfFile[i] # will add entire line but since line only consists of whitespace and the text that is no big deal. Whitespace sequences >2 will be.popd after conversion to CSV string and before writing to the file.
                    else:
                        #empty line
                        pass
                else:
                    # first element line may also be incomplete as in repair invoices... 
                    # thus check for incomplete non empty line
                    matcherObj = regexEmptyLine.match(linesOfFile[i])
                    if matcherObj:
                        #non empty line --> append to elementText, since element Text is empty by default there is no harm in doing so
                        elementLineObj.elementText += linesOfFile[i] # will add entire line but since line only consists of whitespace and the text that is no big deal. Whitespace sequences >2 will be.popd after conversion to CSV string and before writing to the file.
                    else:
                        #empty line
                        pass

    return ["Funktion inkomplett", 0]; # dummy return in case the function is left by the loop terminating without finding the table end somehow.

def cleanupDate(bz):
    matcherObj = regexDateTTMMYYYY.match(bz.belegdatum)
    if matcherObj:
        bz.belegdatum = matcherObj.group(1) + matcherObj.group(2)
    else:
        pass
    return bz

def getGeneralInformation(file,bz):
    file = open(file, "r")
    linesOfFile = file.readlines()
    file.close()
    for line in linesOfFile:
        matcherObj = regexKundennr.match(line)

        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
            bz.gegenkonto = matcherObj.group(2)
        else:
            pass
        matcherObj = regexRechnungsnr.match(line)

        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
            bz.belegfeld1 = matcherObj.group(2)
        else:
            pass

        matcherObj = regexGutschriftsnr.match(line)

        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
            bz.belegfeld1 = matcherObj.group(2)
        else:
            pass

        matcherObj = regexBelegdatum.match(line)
        
        if matcherObj:
            bz.buchungstext += matcherObj.group(1)
            bz.belegdatum = matcherObj.group(2)
        else:
            pass

        matcherObj = regexAufzugsnr.match(line)

        if matcherObj:
            bz.belegfeld2 = matcherObj.group(1)
        else:
            pass

        matcherObj = regexBuchungstext.match(line)

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

    if bz.buchungstext.replace(" ","") == "":
        # maybe Gutschrift -> metadata is shifted downwards
        startOfAddressFieldFound = 0
        for i in range(0,len(linesOfFile)):
            if linesOfFile[i].__contains__("ATB-Aufzugstechnik GmbH, Poensgen u. Pfahler Str. 4, 66386 St. Ingbert"):
                startOfAddressFieldFound = 1
            elif linesOfFile[i].__contains__("Gutschrift"):
                break
            elif startOfAddressFieldFound == 1:
                bz.buchungstext += linesOfFile[i]
            else:
                pass # should be unreachable
        bz.buchungstext = bz.buchungstext.replace("  ", "").replace("\n", " ")
    else:
        # field already filled
        pass

    return bz

def main():
    if (
            not (debuggingActive == 1)
            and not (len(sys.argv) == 3)
       ):
        # incorrect parameter count
        print("Aufrufkonvention: toCSV.py Eingabeordner Ausgabedatei.csv")
        exit()
    else:
        #correct parameter count
        inputfoldername = ""
        outputfilename = ""
        if debuggingActive == 1:
            inputfoldername = "c:\\users\\marc\\Desktop\\ATB Sachen\\Programm"
            outputfilename = "out.csv"
        else:
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
            if platform.system() == "Windows":
                #txtfilelist = ["AR_23400001_20230103.pdf.txt", "AR_23400002_20230103.pdf.txt", "AR_23400003_20230103.pdf.txt"]
                #txtfilelist = ["AR_23400004_20230103.pdf.txt"]
                #txtfilelist = ["AR_23400002_20230103.pdf.txt"]
                txtfilelist = ["AR_23400816_20230116.pdf.txt"]
            else:
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
                returnedBZ = getGeneralInformation(file,bz)
                returnedLines, iterator = getSpecialInformation(file,returnedBZ)
                if iterator > 0:
                    for line in returnedLines:
                        line.umsatz = line.umsatz.replace(".",",")
                        if line.umsatz == "":
                            line.umsatz = "0,00"
                        elif not line.umsatz.__contains__(","):
                            line.umsatz += ",00"
                        else:
                            #umsatz has a value including a comma thus do not change
                            pass
                        line = cleanupDate(line)
                        outputfile.write(re.sub(" +"," ",line.toCSV_String()) + "\n")
                else:
                    pass # empty returned Array --> file error

main() # call main at start of programm

