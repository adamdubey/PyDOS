import os
from time import localtime
from sys import stdin,implementation,path
if not '/lib' in path:
    path.insert(0,'/lib')
path.append('/PyBasic')
try:
    from pydos_ui import Pydos_ui
except ImportError:
    Pydos_ui = None
try:
    from pydos_ui import input
except ImportError:
    pass

import gc
imp = "B"
if implementation.name.upper() == "MICROPYTHON":
    from micropython import mem_info
    imp = "M"
elif implementation.name.upper() == "CIRCUITPYTHON":
    from supervisor import runtime
    imp = "C"

gc.collect()
if 'threshold' in dir(gc):
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

# The first string may contain wildcards
def _match(first, second):

    # If we reach end of both strings, we are done
    if len(first) == 0 and len(second) == 0:
        return True

    # Make sure that the characters after '*' are present
    # in second string. Can't contain two consecutive '*'
    if len(first) > 1 and first[0] == '*' and  len(second) == 0:
        return False

    if (len(first) > 1 and first[0] == '?') or (len(first) != 0
        and len(second) !=0 and first[0] == second[0]):
        return _match(first[1:],second[1:]);

    if len(first) !=0 and first[0] == '*':
        return _match(first[1:],second) or _match(first,second[1:])

    return False

def calcWildCardLen(wldCLen,recursiveFail):
    wldCLen += 1
    if not recursiveFail and wldCLen < 90:
        try:
            (wldCLen,recursiveFail) = calcWildCardLen(wldCLen,recursiveFail)
        except:
            recursiveFail = True

    return (wldCLen,recursiveFail)

def PyDOS():

    global envVars
    if "envVars" not in globals().keys():
        envVars = {}
    _VER = "1.18"
    if imp == "B":
        if os.name.upper() == "POSIX":
            slh = '/'
        else:
            slh = '\\'
    else:
        slh = '/'
    prmpVals = ['>','(',')','&','|','\x1b','\b','<','=',' ',_VER,'\n','$']

    print("Starting Py-DOS...")
    envVars["PATH"] = slh+";/PyBasic"
    envVars["PROMPT"] = "$C$R$F$P$G"
    envVars["LIB"] = ";".join(path[1:])
    if Pydos_ui:
        (envVars["_scrHeight"],envVars["_scrWidth"]) = Pydos_ui.get_screensize()
    else:
        envVars["_scrHeight"] = 24
        envVars["_scrWidth"] = 80
    scrWdth = int(envVars["_scrWidth"])

    wldCLen = 0
    recursiveFail = False

    (wldCLen,recursiveFail) = calcWildCardLen(wldCLen,recursiveFail)

    if imp == "C":
        wldCLen = max(1,wldCLen-6)
    else:
        wldCLen = max(1,wldCLen-2)

    if wldCLen < 40:
        print("*Warning* wild card length set to: ",wldCLen)
    gc.collect()

    def anyKey():
        print("Press any key to continue . . . .",end="")
        if Pydos_ui:
            while not Pydos_ui.serial_bytes_available():
                pass
            keyIn = Pydos_ui.read_keyboard(1)
        else:
            if imp == "C":
                while not runtime.serial_bytes_available:
                    pass
            keyIn = stdin.read(1)
        print("")
        return(keyIn)

    def scrnPause(swPause,nLines,scrnLine,scrnEnd=None):
        quit = False
        i = 0
        for sLine in scrnLine:
            i += 1
            if swPause and nLines >= int(envVars["_scrHeight"])-1:
                key = anyKey()
                nLines = 0
                if key in "QqCc":
                    quit = True
                    break
            if sLine is not None:
                if scrnEnd is None or i<len(scrnLine):
                    print(sLine)
                    nLines += 1
                else:
                    print(sLine,end="")
        return (quit,nLines)

    def weekDay():
        offset = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
        week   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
        month = localtime()[1]
        day = localtime()[2]
        year = localtime()[0]
        afterFeb = 1
        if month > 2: afterFeb = 0
        aux = year - 1700 - afterFeb
        # dayOfWeek for 1700/1/1 = 5, Friday
        dayOfWeek  = 5
        # days betweem current date and 1700/1/1
        dayOfWeek += (aux + afterFeb) * 365
        # leap year
        dayOfWeek += aux / 4 - aux / 100 + (aux + 100) / 400
        dayOfWeek += offset[month - 1] + (day - 1)
        dayOfWeek %= 7
        return week[int(dayOfWeek)]

    def exCmd(cFile,passedIn):
        try:
            with open(cFile) as cf:
                if passedIn.find("'") > -1:
                    exec('passedIn = "'+passedIn+'"\n'+cf.read())
                else:
                    exec("passedIn = '"+passedIn+"'\n"+cf.read())
        except Exception as err:
            print("*ERROR* Exception:",str(err),"in",cFile)

        return

    def chkPath(tstPath):
        validPath = True
        simpPath = ""

        if tstPath != []:
            savDir = os.getcwd()
            for path in tstPath:
                path = path.replace("C:","")
                if path == "":
                    os.chdir(slh)
                elif os.getcwd() == slh and path == "..":
                    validPath = False
                    break
                elif path == ".":
                    continue
                elif path == ".." and len(os.getcwd().split(slh)) == 2:
                    os.chdir(slh)
                elif path == "..":
                    os.chdir("..")
                elif path in os.listdir() and (os.stat(path)[0] & (2**15) == 0):
                    os.chdir(path)
                else:
                    validPath = False
                    break

            if validPath:
                simpPath = os.getcwd()
            os.chdir(savDir)

        return((validPath,simpPath))

    def absolutePath(argPath,currDir):

        if argPath[0] == slh:
            fullPath = argPath
        elif currDir == slh:
            fullPath = slh+argPath
        else:
            fullPath = currDir+slh+argPath

        if len(fullPath) > 1 and fullPath[-1] == slh:
            fullPath = fullPath[:-1]

        return(fullPath)

    def prDir(dirPath,swBits):
        wideCols = int(scrWdth/16)

        def dirLoop(tmpDir,lastDir,isFile,swPause,swWide,swRecur,prSum, \
            nLines=0,nFiles=0,tFSize=0,nDirs=0):

            wideCount = 0
            dirHeadPrntd = False
            quit = False

            if "*" in lastDir or "?" in lastDir or isFile:
                dirPat = lastDir
                lastDir = ""
            else:
                dirPat = None

            dPath = tmpDir+(slh if tmpDir[-1] != slh else "")+lastDir
            dPath = dPath + (slh if dPath[-1] != slh else "")
            if dPath == slh+".":
                dPath = slh
                lastDir = ""

            if dirPat is None:
                (quit,nLines) = scrnPause(swPause,nLines,["","Directory of "+dPath])
                dirHeadPrntd = True
                nDirs += 2
                if swWide:
                    if wideCols > 1:
                        (quit,nLines) = scrnPause(swPause,nLines, \
                            ["[.]             [..]            "],"")
                        wideCount += 2
                    else:
                        (quit,nLines) = scrnPause(swPause,nLines,["[.]","[..]"],"")
                        wideCount = 1
                else:
                    scrAdj1 = 52 - min(scrWdth,52)
                    (quit,nLines) = scrnPause(swPause,nLines, \
                        ["."+" "*(23-scrAdj1)+"<DIR>",".."+" "*(22-scrAdj1)+"<DIR>"])

            for i in range(2):
                for _dir in sorted([x for x in os.listdir(dPath) if (os.stat(dPath+x)[0]&(32768))>>15==i],key=str.lower):
                    if (dirPat is None or _match(dirPat,_dir[:wldCLen])) and not quit:

                        if not dirHeadPrntd:
                            (quit,nLines) = scrnPause(swPause,nLines,["","Directory of "+dPath])
                            if quit:
                                break
                            dirHeadPrntd = True

                        if i == 0: 
                            fSize = 0
                            nDirs += 1
                        else:
                            fSize = str(os.stat(dPath+_dir)[6])
                            tFSize += int(fSize)
                            nFiles += 1

                        fTime = localtime(max(min(2145916800,os.stat(dPath+_dir)[9]),946684800))

                        if swWide:
                            if wideCount >= wideCols:
                                wideCount = 0
                                print()
                                nLines += 1
                            wideCount += 1
                            if i == 0:
                                (quit,nLines) = scrnPause(swPause,nLines, \
                                    ["["+_dir[:13]+"]"+" "*(14-len(_dir[:13]))],"")
                            else:
                                (quit,nLines) = scrnPause(swPause,nLines, \
                                    [_dir[:15]+" "*(16-len(_dir[:15]))],"")
                        else:
                            if i == 0:
                                scrAdj1 = 52 - min(scrWdth,52)
                                scrAdj2 = min(13,65-min(scrWdth,65))
                                (quit,nLines) = scrnPause(swPause,nLines, \
                                    [_dir[:max(8,scrWdth-26)]+" "*(24-len(_dir)-scrAdj1)+"<DIR>"+" "*(18-scrAdj2)+"%2.2i-%2.2i-%4.4i %2.2i:%2.2i" % (fTime[1], fTime[2], fTime[0], fTime[3], fTime[4])])
                            else:
                                scrAdj1 = 65 - min(scrWdth,65)
                                (quit,nLines) = scrnPause(swPause,nLines, \
                                    [_dir[:max(8,scrWdth-20-len(fSize))]+" "*(36-len(_dir)+10-len(fSize)-scrAdj1)+fSize+" %2.2i-%2.2i-%4.4i %2.2i:%2.2i" % (fTime[1], fTime[2], fTime[0], fTime[3], fTime[4])])

                        if quit:
                            break

            if not quit:
                if swWide:
                    if dirHeadPrntd:
                        print()
                        nLines += 1

                if swRecur:
                    for _dir in sorted(os.listdir(dPath), key=str.upper):
                        if (os.stat(dPath+_dir)[0] & (32768) == 0) == True:
                            (nLines,nFiles,tFSize,nDirs,quit) = \
                                dirLoop(dPath+_dir,(dirPat if dirPat is not None else ""), \
                                    isFile,swPause,swWide,swRecur,False, \
                                    nLines,nFiles,tFSize,nDirs)
                        if quit:
                            break

                if prSum and not quit:
                    try:
                        availDisk = os.statvfs(dPath)[1]*os.statvfs(dPath)[4]
                    except:
                        availDisk = 0

                    scrAdj1 = 65 - min(scrWdth,65)
                    (quit,nLines) = scrnPause(swPause,nLines, \
                        [" "*(4-len(str(nFiles)))+" "+str(nFiles)+" File(s)"+" "*(32-len(str(tFSize))-scrAdj1)+" "+str(tFSize)+" Bytes.", \
                        " "*(4-len(str(nDirs)))+" "+str(nDirs)+" Dir(s)"+" "*(33-len(str(availDisk))-scrAdj1)+" "+str(availDisk)+" Bytes free.",""],"")

            return (nLines,nFiles,tFSize,nDirs,quit)

        if swBits & (swAllB-int('010110',2)):
            print("Illegal switch, Command Format: DIR[/p][/w][/s] [path][file]")
            return

        savDir = os.getcwd()
        fullPath = absolutePath(dirPath,savDir)

        pathDirs = fullPath.split(slh)
        lastDir = pathDirs.pop(-1)

        (validPath, tmpDir) = chkPath(pathDirs)

        if validPath:

            os.chdir(tmpDir)

            if tmpDir == slh:
                pathDirs = [""]
            else:
                pathDirs = tmpDir.split(slh)

            # Check for relative directory from possible mount point root
            if len(pathDirs) == 2:
                if lastDir == ".":
                    os.chdir(slh)
                    lastDir = tmpDir[1:]
                elif lastDir == "..":
                    os.chdir(slh)
                    lastDir = ""

            tmpDir = os.getcwd()

            if lastDir in os.listdir() or lastDir in ".." or "*" in lastDir or "?" in lastDir or \
                swBits & int('000010',2):

                if lastDir in os.listdir():
                    if os.stat(slh if lastDir == "" else lastDir)[0] & (2**15) == 0:
                        isFile = False
                    else:
                        isFile = True
                else:
                    if lastDir in ".." or (tmpDir == "/" and lastDir == ""):
                        isFile = False
                    else:
                        isFile = True

                dirLoop(tmpDir,lastDir,isFile,bool(swBits&int('000100',2)),bool(swBits&int('010000',2)),bool(swBits&int('000010',2)),True)
            else:
                print("File",dirPath,"not found. (1)")

            os.chdir(savDir)
        else:
            print("File",dirPath,"not found. (2)")

        return

    def filecpy(file1,file2):
        gc.collect()
        with open(file2, "wb") as fCopy:
            with open(file1, 'rb') as fOrig:
                for line in fOrig:
                    fCopy.write(line)
        gc.collect()
        return

    def delFiles(Dir,File,Recurs,removDirs):
        for _dir in os.listdir(Dir[:(-1 if Dir != slh else None)]):
            if _match(File,_dir[:wldCLen]):
                if _dir == _dir[:wldCLen]:
                    if os.stat(Dir+_dir)[0] & (2**15) != 0:
                        try:
                            os.remove(Dir+_dir)
                            print(Dir+_dir,"deleted.")
                        except Exception as err:
                            print("Unable to delete: "+Dir+_dir+", Exception:",str(err))
                            break
                    elif Recurs:
                        delFiles(Dir+_dir+slh,'*',Recurs,removDirs)
                        if removDirs:
                            if os.getcwd() == Dir+_dir:
                                os.chdir("..")
                            try:
                                os.rmdir(Dir+_dir)
                            except Exception as err:
                                print("Unable to remove: "+Dir+_dir+", Exception:",str(err))
                                break
                else:
                    print("Unable to delete: "+Dir+_dir+". Filename too long for wildcard operation.")
            elif Recurs and not removDirs and os.stat(Dir+_dir)[0] & (2**15) == 0:
                delFiles(Dir+_dir+slh,File,Recurs,removDirs)

    def setCondCmd(args,i,condResult):
        condCmd = ""
        foundElse = False

        for _ in args[i:]:

            if condResult:
                if _.upper() == "ELSE":
                    break
                condCmd += (_+" ")
            else:
                if foundElse:
                    condCmd += (_+" ")
                else:
                    if _.upper() == "ELSE":
                        foundElse = True

        return condCmd

    def readBATFile(BATfile):
        batIndex = [0]
        batLabels = {}
        batLineNo = 0
        for batLine in BATfile:
            batIndex.append(batIndex[batLineNo]+len(batLine))
            batLineNo += 1
            if batLine.strip() != "":
                if batLine.strip()[0] == ":" and len(batLine.strip().split(" ")[0]) > 1:
                    batLabels[batLine.strip().split(" ")[0][1:]] = [batLineNo,batIndex[batLineNo]]
        BATfile.seek(0)
        del batIndex,batLineNo,batLine

        return batLabels

    batEcho = True
    cmd = ""
    condCmd = ""
    os.chdir(slh)
    if "autoexec.bat" in ",".join(os.listdir()).lower().split(','):
        activeBAT = True
        BATfile = open(os.listdir()[(",".join(os.listdir()).lower().split(",")).index("autoexec.bat")])
        batLabels = readBATFile(BATfile)
        batLineNo = 0
        batParams = []
    else:
        activeBAT = False
        gc.collect()

    while True:
        if condCmd != "":
            cmdLine = condCmd
            condCmd = ""
        else:
            if activeBAT:
                cmdLine = BATfile.readline()
                i=1
                for param in batParams:
                    cmdLine = cmdLine.replace('%'+str(i),param)
                    i+=1
                    if i>9:
                        break

                batLineNo += 1
                if cmdLine == "":
                    activeBAT = False
                    batEcho = True
                    BATfile.close()
                    gc.collect()
                elif batEcho and cmdLine[0] !="@":
                    print(cmdLine,end="")
                elif cmdLine[0] == "@":
                    cmdLine = cmdLine[1:]

            else:
                prompt = "\n"
                for prmpToken in envVars.get('PROMPT','$C$R$F$P$G').upper().replace("$$","$.").split("$")[1:]:
                    if prmpToken == 'R':
                        if 'mem_free' in dir(gc):
                            prompt += str(gc.mem_free())
                    elif prmpToken == 'D':
                        prompt += "%2.2i/%2.2i/%4.4i" % (localtime()[1], localtime()[2], localtime()[0])
                    elif prmpToken == 'T':
                        prompt += "%2.2i:%2.2i:%2.2i" % (localtime()[3], localtime()[4], localtime()[5])
                    elif prmpToken == 'P':
                        prompt += os.getcwd()
                    else:
                        prompt += prmpVals['GCFABEHLQSV_.'.find(prmpToken)]
                cmdLine = input(prompt)

        cmdLine = cmdLine.strip()

        envFound = False
        fndVar = ""
        newCmdLine = ""
        for _ in cmdLine:
            if not envFound:
                if _ == "%":
                    envFound = True
                    doublepct = True
                else:
                    newCmdLine += _
            else:
                if _ == "%":
                    if doublepct:
                        newCmdLine += "%"
                    envFound = False
                    newCmdLine += str(envVars.get(fndVar,""))
                    fndVar = ""
                else:
                    doublepct = False
                    fndVar += _
        cmdLine = newCmdLine

        args = cmdLine.split(" ")

        quotedArg = False
        if len(args) > 1:
            i = 0
            iEnd = len(args)
            for _ in range(0, iEnd):
                if args[i].strip() == "":
                    args.pop(i)
                elif quotedArg:
                    if args[i].find('"') > -1 and args[i].find('"') != len(args[i])-1:
                        break
                    elif args[i][-1] == '"':
                        args[i-1] = args[i-1] + " " + args.pop(i)[:-1]
                        quotedArg = False
                    else:
                        args[i-1] = args[i-1] + " " + args.pop(i)
                elif args[i][0] == '"':
                    if args[i][-1] != '"':
                        args[i] = args[i][1:]
                        i += 1
                        quotedArg = True
                    else:
                        args[i] = args[i][1:-1]
                        i += 1
                else:
                    i += 1

        if cmdLine != "" and cmdLine[0] != '/':
            switches = (args[0].upper()).split('/')
            cmd = switches.pop(0)
        else:
            switches = ""
            cmd = args[0]

        # Error=1, (S)Recur=2, (P)Pause=4, (Y)Conf=8, (W)Wide=16, (D)debug=32, (Q)uiet=64
        swBits = 0
        swAllB = int('1111111',2)
        for i in range(len(switches)):
            swBits = swBits | (2**('SPYWDQ'.find(switches[i])+1))

        if quotedArg:
            print("Mismatched quotes.")
            cmd = ""

        if cmd in ["DELETE","DEL","TYPE","MORE","MKDIR","MD","RMDIR","RD","COPY", \
                   "CHDIR","CD","RENAME","REN","MOVE"]:
            if len(args) > 1:
                savDir = os.getcwd()
                args[1] = absolutePath(args[1],savDir)
                aPath = args[1].split(slh)
                if cmd not in ["RMDIR","RD","CHDIR","CD"]:
                    newdir = aPath.pop(-1)
                (validPath,tmpDir) = chkPath(aPath)
                if cmd in ["DELETE","DEL","TYPE","MORE","MKDIR","MD"]:
                    if tmpDir == "" or tmpDir[-1] != slh:
                        tmpDir += slh

        if cmd == "" or cmd == "REM":
            continue
        elif cmd == "DIR":
            if len(args) == 1:
                prDir(os.getcwd().replace("C:",""),swBits)
            elif len(args) == 2:
                prDir(args[1],swBits)
            else:
                print("Too many arguments. Command Format: DIR/p/w [path][file]")

        elif cmd == "DATE":
            print("The current date is: "+weekDay()+" %2.2i/%2.2i/%4.4i" % (localtime()[1], localtime()[2], localtime()[0]))

        elif cmd == "TIME":
            print("The current time is: %2.2i:%2.2i:%2.2i" % (localtime()[3], localtime()[4], localtime()[5]))

        elif cmd == "MEM":
            gc.collect()
            print("\n%10i Kb free conventional memory" % (int(gc.mem_free()/1000)))
            print("%10i Kb used conventional memory" % (int(gc.mem_alloc()/1000)))
            if imp == "M":
                if 'threshold' in dir(gc):
                    print("%10i Kb current threshold value" % (int(gc.threshold()/1000)))

                if swBits & int('010000',2):
                    print(mem_info(1))
                elif swBits:
                    print("Illegal switch, Command Format: mem[/d]")

        elif cmd == "VER":
            print("PyDOS [Version "+_VER+"]")

        elif cmd == "ECHO":
            if len(args) == 1:
                print("Echo is "+("on." if batEcho else "off."))
            else:
                if args[1].upper() == 'ON':
                    batEcho = True
                elif args[1].upper() == 'OFF':
                    batEcho = False
                else:
                    print(cmdLine[5:])

        elif cmd == "PAUSE":
            anyKey()

        elif cmd[0] == ":" and activeBAT:
            if len(args[0]) <= 1 or len(args) != 1:
                print("Invalid batch label")
                condCmd = "exit"

        elif cmd == "GOTO" and activeBAT:
            if len(args) == 2:
                try:
                    BATfile.seek(batLabels[args[1]][1])
                except:
                    print("Invalid Goto label:",args[1])
                    condCmd = "exit"

                batLineNo = batLabels.get(args[1],[batLineNo+1,0])[0]
            else:
                print("Invalid Goto label:",cmdLine)
                condCmd = "exit"

        elif cmd == "IF" and activeBAT:
            condResult = False

            if len(args) < 3:
                print("Invalid command format:",cmdLine)
                condCmd = "exit"
            else:
                i = 1
                notlogic = False
                if args[1].upper() == "NOT":
                    notlogic = True
                    i = 2

                if args[i].strip().upper() == 'ERRORLEVEL':
                    i += 1
                    if len(args) > i and args[i].isdigit():
                        if str(envVars.get('errorlevel')).isdigit() and int(envVars.get('errorlevel')) == int(args[i]):
                            condResult = True

                        if notlogic:
                            condResult = not condResult

                        i += 1
                        condCmd = setCondCmd(args,i,condResult)
                    else:
                        print("Invalid conditional ERRORLEVEL:",cmdLine)
                        condCmd = "exit"

                elif args[i].strip().upper() == 'EXIST':
                    i += 1
                    if len(args) > i:
                        savDir = os.getcwd()
                        args[i] = absolutePath(args[i],savDir)

                        aPath = args[i].split(slh)
                        newdir = aPath.pop(-1)
                        (validPath, tmpDir) = chkPath(aPath)
                        if tmpDir == "" or tmpDir[-1] != slh:
                            tmpDir += slh

                        if validPath and newdir in os.listdir(tmpDir[:(-1 if tmpDir != slh else None)]):
                            condResult = True
                        if notlogic:
                            condResult = not condResult

                        i += 1
                        condCmd = setCondCmd(args,i,condResult)

                    else:
                        print("Invalid conditional EXIST:",cmdLine)
                        condCmd = "exit"
                else:
                    # string comparison
                    if len(args) > i:
                        string1 = args[i]
                        if "==" in args[i]:
                            string1 = args[i].split("==")[0]
                            if args[i][-1] != "=":
                                string2 = args[i].split("==")[-1]
                            else:
                                i += 1
                                if len(args) > i:
                                    string2 = args[i]
                                else:
                                    print("Invalid string conditional:",cmdLine)
                                    condCmd = "exit"
                        elif len(args) > i+1:
                            i += 1
                            if "==" in args[i]:
                                if len(args[i]) > 2:
                                    string2 = args[i].split("==")[-1]
                                else:
                                    i+=1
                                    if len(args) > i:
                                        string2 = args[i]
                                    else:
                                        print("Invalid string conditional:",cmdLine)
                                        condCmd = "exit"
                            else:
                                print("Invalid string conditional:",cmdLine)
                                condCmd = "exit"
                        else:
                            print("Invalid string conditional:",cmdLine)
                            condCmd = "exit"


                        if condCmd != "exit":
                            if string1 == string2:
                                condResult = True
                            if notlogic:
                                condResult = not condResult

                            i += 1
                            condCmd = setCondCmd(args,i,condResult)
                    else:
                        print("Invalid string conditional:",cmdLine)
                        condCmd = "exit"

        elif cmd == "SET":
            if len(args) == 1:
                for _ in sorted(envVars):
                    print(_+"=",envVars[_],sep="")
            else:
                args = cmdLine.split(" ")
                args.pop(0)
                envCmd = (" ".join(args)).split("=")
                envCmdVar = envCmd.pop(0).strip()

                if len(switches) <= 1:
                    if len(switches) == 0:
                        tmp = "=".join(envCmd).strip()
                    elif switches[0] == 'A':
                        # Replace all possible environment variables with their values
                        envCmd = "=".join(envCmd)
                        for _ in " %*()-+/":
                            envCmd = envCmd.replace(_," ")
                        envCmd = envCmd.split(" ")

                        for _ in envCmd:
                            if _ != "":
                                if _[0].isalpha() or _[0] == "_":
                                    cmdLine = cmdLine.replace(_.strip(),str(envVars.get(_,0)))

                        # Evaluate right sight of = after value substituion
                        args = cmdLine.split(" ")
                        args.pop(0)
                        envCmd = (" ".join(args)).split("=")
                        envCmdVar = envCmd.pop(0).strip()
                        try:
                            envVars[envCmdVar] = str(eval("=".join(envCmd).strip()))
                        except:
                            envVars[envCmdVar] = "0"
                    elif switches[0] == "P":
                        tmp = input("=".join(envCmd).strip()+" ")
                    else:
                        print("Illegal switch, Command Format: SET[/a|/p] [variable = [string|expression]]")

                    if len(switches) == 0 or switches[0] == "P":
                        if tmp != "":
                            envVars[envCmdVar] = tmp
                        else:
                            if Pydos_ui:
                                (tHeight,tWidth) = Pydos_ui.get_screensize()
                            else:
                                tHeight = 24
                                tWidth = 80
                            if envCmdVar == "_scrHeight":
                                envVars["_scrHeight"] = tHeight
                            elif envCmdVar == "_scrWidth":
                                envVars["_scrWidth"] = tWidth
                            elif envVars.get(envCmdVar) != None:
                                envVars.pop(envCmdVar)
                    
                    scrWdth = int(envVars["_scrWidth"])
                    if envCmdVar == 'LIB':
                        path.clear()
                        path.extend(['']+envVars["LIB"].split(';'))
                else:
                    print("Illegal switch, Command Format: SET[/a|/p] [variable = [string|expression]]")

        elif cmd in ["PROMPT","PATH"]:
            if len(args) == 1:
                print(cmd+"="+envVars.get(cmd,""))
            else:
                envVars[cmd] = args[1]

        elif cmd in ["RENAME","REN","MOVE"]:
# todo: allow source to be file and target directory?
# Wildcard renames
# renames across sd mount points

            if len(args) == 3:
# Check that first argument has a valid path and exists
                if validPath and newdir in os.listdir(tmpDir) and args[1][-1] != slh:

                    args[2] = absolutePath(args[2],savDir)
                    aPath2 = args[2].split(slh)
                    newdir2 = aPath2.pop(-1)
                    (validPath, tmpDir2) = chkPath(aPath2)

                    if newdir2 == '*':
                        newdir2 = newdir
# Second argument has valid path
                    if validPath and args[2][-1] != slh and '?' not in newdir2 and \
                        '*' not in newdir2 and newdir2 !="." and newdir2 != "..":
                        
# second argument doesn't specify an existing target
                        if newdir2 not in os.listdir(tmpDir2):
                            currDRen = False
                            if os.stat(tmpDir+slh+newdir)[0] & (2**15) == 0:
                                if tmpDir+slh+newdir == os.getcwd():
                                    currDRen = True
                            os.rename(tmpDir+("" if tmpDir[-1] == slh else slh)+newdir, \
                                    tmpDir2+("" if tmpDir2[-1] == slh else slh)+newdir2)
                            if currDRen:
                                os.chdir(tmpDir2)

                        else:
                            print("Target file exists")
                    else:
                        print("Invalid target:",args[2])
                else:
                    print("Invalid source:",args[1])
            else:
                print("Wrong number of arguments")

        elif cmd in ["DELETE","DEL"]:

            if len(args) == 2:
                if validPath:
                    if not (swAllB-int('000010',2)) & swBits:
                        if "*" in newdir or "?" in newdir:
                            ans = "Y"
                            if newdir == "*" or newdir == "*.*":
                                ans = input(tmpDir+newdir+", Are you sure (y/n)? ").upper()

                            if ans == "Y":
                                delFiles(tmpDir,newdir,bool(swBits&int('000010',2)),False)
                        else:
                            if newdir in os.listdir(tmpDir[:(-1 if tmpDir != slh else None)]):
                                if os.stat(tmpDir+newdir)[0] & (2**15) != 0:
                                    os.remove(tmpDir+newdir)
                                    print(tmpDir+newdir,"deleted.")
                                else:
                                    ans = input(tmpDir+newdir+slh+"*, Are you sure (y/n)? ").upper()
                                    if ans == "Y":
                                        delFiles(tmpDir+newdir+slh,'*',bool(swBits&int('000010',2)),False)
                            else:
                                if swBits & int('000010',2):
                                    ans = input(tmpDir+newdir+slh+"*, Are you sure (y/n)? ").upper()
                                    if ans == "Y":
                                        delFiles(tmpDir,newdir,True,False)
                                else:
                                    print("Unable to delete: "+tmpDir+newdir+". File not found.")
                    else:
                        print("Illegal switch, Command Format: DEL[/s] [path][file]")
                else:
                    print("Unable to delete: "+tmpDir+newdir+". File not found.")
            else:
                print("Illegal Path.")

        elif cmd in ["TYPE","MORE"]:

            if len(args) == 2:
                if validPath and newdir in os.listdir(tmpDir[:(-1 if tmpDir != slh else None)]) and os.stat(tmpDir+newdir)[0] & (2**15) != 0:
                    if cmd == "MORE":
                        swBits = swBits | int('000100',2)

                    if not ((swAllB-int('000100',2)) & swBits):
                        swPause = bool(swBits & int('000100',2))
                        key = " "
                        with open(tmpDir+newdir, "rb") as f:
                            nLines = 0
                            for line in f:
                                istrt = 0
                                while istrt+scrWdth < len(line):
                                    (quit,nLines) = scrnPause(swPause,nLines,[None])
                                    try:
                                        print(line[istrt:istrt+scrWdth].decode())
                                    except:
                                        print(chr(65534)*scrWdth)
                                    nLines += 1
                                    istrt += scrWdth
                                (quit,nLines) = scrnPause(swPause,nLines,[None])
                                if quit:
                                    break
                                try:
                                    print(line[istrt:len(line)].decode(),end="")
                                except:
                                    print(chr(65534)*(len(line)-istrt))
                                nLines += 1
                    else:
                        print("Illegal switch, Command Format: TYPE[/p] [path][file]")
                else:
                    print("Unable to display: "+tmpDir+newdir+". File not found.")
            else:
                print("Illegal Path.")


        elif cmd in ["CHDIR","CD"]:

            if len(args) == 1:
                print(os.getcwd())
            else:
                if validPath:
                    os.chdir(tmpDir)
                else:
                    print("Unable to change to:",args[1])

        elif cmd in ["MKDIR","MD"]:
            if len(args) == 1:
                print("Unable to make .")
            elif len(args) > 2:
                print("Too many arguments")
            else:
                if validPath:
                    if newdir not in os.listdir(tmpDir[:(-1 if tmpDir != slh else None)]):
                        os.mkdir(tmpDir+newdir)
                    else:
                        print("Target name already exists")
                else:
                    print("Invalid path")

        elif cmd in ["RMDIR","RD"]:
            if len(args) == 2 and validPath:
                if not (swBits & (swAllB-int('000010',2))):
                    if tmpDir != slh:
                        if swBits & int('000010',2):
                            ans = input(tmpDir+" Are you sure (y/n)? ").upper()
                            if ans == "Y":
                                delFiles(tmpDir+slh,'*',bool(swBits&int('000010',2)),True)

                        if os.listdir(tmpDir) == []:
                            if os.getcwd() == tmpDir:
                                os.chdir("..")
                            if len(tmpDir.split(slh)) > 2:
                                os.chdir(slh+tmpDir.split(slh)[1])
                            try:
                                os.rmdir(tmpDir)
                            except Exception as err:
                                print("Unable to remove: "+tmpDir+", Exception:",str(err))
                            try:
                                os.chdir(savDir)
                            except:
                                pass
                        else:
                            print("The directory is not empty")
                    else:
                        print("Can not remove root directory")
                else:
                    print("Illegal switch, Command Format: RD[/s] path")
            else:
                print("Invalid path")

        elif cmd == "COPY":

            if (len(args) == 3 or len(args) == 2) and not swBits & (swAllB-int('001000',2)):
                if len(args) == 2:
                    args.append('.')

                nFiles = 0
                earlyError = False
                trailingSlash = False
                if args[1][-1] == slh:
                    print("The source file cannot be a directory")
                    earlyError = True
                if args[2][-1] == slh:
                    trailingSlash = True

# Check that first argument has a valid path, exists and is not a directory file
                if not earlyError and validPath and ("*" in newdir or "?" in newdir or (newdir in os.listdir(tmpDir) and os.stat(tmpDir+(slh if tmpDir[-1] != slh else "")+newdir)[0] & (2**15))) != 0:

                    sourcePath = tmpDir
                    if "*" in newdir or "?" in newdir:
                        wildCardOp = True
                    else:
                        wildCardOp = False

                    enteredArg = args[2]
                    args[2] = absolutePath(args[2],savDir)
                    aPath2 = args[2].split(slh)
                    newdir2 = aPath2.pop(-1)
                    (validPath, tmpDir) = chkPath(aPath2)
                    if newdir2 == "*":
                        newdir2 = "."
                    if "*" in newdir2 or "?" in newdir2:
                        validPath = False

# Second argument has valid path
                    if validPath:
                        gc.collect()
                        targetPath = tmpDir

                        if newdir2 in "..":
                            (validPath,tmpDir) = chkPath((targetPath+(slh if targetPath[-1] != slh else "")+newdir2).split(slh))
                            aPath2 = tmpDir.split(slh)
                            newdir2 = aPath2.pop(-1)
                            targetPath = chkPath(aPath2)[1]
                            if not validPath:
                                print("Impossible Target Error:",args[2])

# Second argument specifies an existing target
                        if newdir2 in os.listdir(targetPath) or (targetPath == slh and newdir2 == ""):

# Second argument target is a file
                            if os.stat(targetPath+(slh if targetPath[-1] != slh else "")+newdir2)[0] & (2**15) != 0:
                                if trailingSlash:
                                    print("Cannot find the specified path: ",enteredArg)
                                elif wildCardOp:
                                    print("Target must be directory for wildcard copy ",enteredArg)

                                elif sourcePath == targetPath and newdir == newdir2:
                                    print("The file cannot be copied onto itself")

                                elif swBits & int('001000',2) or input("Overwrite "+args[2]+"? (y/n): ").upper() == "Y":
                                    os.remove(targetPath+(slh if targetPath[-1] != slh else "")+newdir2)
                                    filecpy(sourcePath+(slh if sourcePath[-1] != slh else "")+newdir,targetPath+(slh if targetPath[-1] != slh else "")+newdir2)
                                    nFiles += 1

# Second argument target is a directory
                            else:
                                if sourcePath == "" or sourcePath[-1] != slh:
                                    sourcePath += slh
                                if targetPath == "" or targetPath[-1] != slh:
                                    targetPath += slh

                                if wildCardOp:
                                    ans = ""
                                    for _dir in os.listdir(sourcePath[:(-1 if sourcePath != slh else None)]):
                                        if os.stat(sourcePath+_dir)[0] & (2**15) != 0 and _match(newdir,_dir[:wldCLen]):
                                            print("copy",sourcePath+_dir,"to",targetPath+newdir2+("" if newdir2 == "" else slh)+_dir)
                                            if _dir in os.listdir(targetPath+newdir2):
                                                if sourcePath == targetPath+newdir2+("" if newdir2 == "" else slh):
                                                    print("The file cannot be copied onto itself")
                                                    break
                                                else:
                                                    if ans != "A" and not swBits & int('001000',2):
                                                        ans = input("Overwrite "+targetPath+newdir2+("" if newdir2 == "" else slh)+_dir+"? (y/n/(q)uit/(a)ll): ").upper()
                                                    if ans  == "Y" or ans == "A" or swBits & int('001000',2):
                                                        filecpy(sourcePath+_dir,targetPath+newdir2+("" if newdir2 == "" else slh)+_dir)
                                                        nFiles += 1
                                                    elif ans == "Q":
                                                        break
                                            else:
                                                filecpy(sourcePath+_dir,targetPath+newdir2+("" if newdir2 == "" else slh)+_dir)
                                                nFiles += 1
                                            gc.collect()

                                elif newdir in os.listdir(targetPath+newdir2):
                                    if sourcePath == targetPath+newdir2+("" if newdir2 == "" else slh):
                                        print("The file cannot be copied onto itself")
                                    elif swBits & int('001000',2) or input("Overwrite "+targetPath+newdir2+("" if newdir2 == "" else slh)+newdir+"? (y/n): ").upper() == "Y":
                                        os.remove(targetPath+newdir2+("" if newdir2 == "" else slh)+newdir)
                                        filecpy(sourcePath+newdir,targetPath+newdir2+("" if newdir2 == "" else slh)+newdir)
                                        nFiles += 1

                                else:
                                    filecpy(sourcePath+newdir,targetPath+newdir2+("" if newdir2 == "" else slh)+newdir)
                                    nFiles += 1
# Second argument is a new file
                        else:
                            if trailingSlash or wildCardOp:
                                if wildCardOp:
                                    print("Target must be directory for wildcard copy ",enteredArg)
                                else:
                                    print("Cannot find the specified path: ",enteredArg)
                            else:
                                filecpy(sourcePath+(slh if sourcePath[-1] != slh else "")+newdir,targetPath+(slh if targetPath[-1] != slh else "")+newdir2)
                                nFiles += 1

                        print(" "*7,nFiles,"files(s) copied.")
                    else:
                        print("Invalid destination:",args[2])
                else:
                    print("No such file:",args[1])
            else:
                if swBits & (swAllB-int('001000',2)):
                    print("Illegal switch, Command Format: COPY[/y] [path]file [path][file]")
                else:
                    print("Wrong number of arguments")

        elif cmd == "PEXEC":
            if not (swAllB-int('1000000',2)) & swBits:
                if len(args) == 1:
                    pcmd = input("=>> ")
                else:
                    pcmd = " ".join(args[1:])
                try:
                    exec(pcmd)
                    envVars['errorlevel'] = '0'
                except Exception as err:
                    if not swBits & int('1000000',2):
                        print("*ERROR* Exception:",str(err))
                    envVars['errorlevel'] = '1'
                del pcmd
            else:
                print("Illegal switch, Command Format: PEXEC[/q] python command")

        elif cmd == "EXIT":
            if activeBAT:
                if len(args) > 1:
                    envVars['errorlevel'] = args[1]
                activeBAT = False
                batEcho = True
                BATfile.close()
            else:
                threadFound = True
                try:
                    testthreadLock = threadLock
                except:
                    threadFound = False

                if threadFound:
                    import _thread

                    if threadLock.locked():
                        threadLock.release()
                    else:
                        threadLock.acquire()

                break

        else:
            savDir = os.getcwd()
            args[0] = absolutePath(args[0],savDir)

            aPath = args[0].split(slh)
            if 'xcopy' in aPath:
                envVars["_switches"] = [i.upper() for i in aPath[aPath.index('xcopy')+1:]]
                aPath = aPath[0:aPath.index('xcopy')+1]
            newdir = aPath.pop(-1)
            (validPath, tmpDir) = chkPath(aPath)
            if tmpDir == "" or tmpDir[-1] != slh:
                tmpDir += slh

            args = [('"'+i+'"' if i.find(" ") != -1 else i) for i in args]
            if len(args) == 1:
                passedIn = ""
                batParams = []
            elif len(args) > 1:
                passedIn = " ".join(args[1:])
                batParams = args[1:]

            gc.collect()
            batFound = ""

            cmdFound = False
            for tmpDir in [tmpDir]+(envVars.get('PATH',"").split(";") if envVars.get('PATH',"") != "" else []):
                if tmpDir[-1] != slh:
                    tmpDir += slh
                curDLst = os.listdir(tmpDir[:(-1 if tmpDir != slh else None)])
                curDLst_LC = ",".join(curDLst).lower().split(",")
                if  ((newdir.split("."))[-1]).upper() == "PY":
                    if validPath and newdir in curDLst and os.stat(tmpDir+newdir)[0] & (2**15) != 0:

                        exCmd(tmpDir+newdir,passedIn)
                        cmdFound = True
                        break
                elif ((newdir.split("."))[-1]).upper() == "BAT":
                    if validPath and newdir in curDLst and os.stat(tmpDir+newdir)[0] & (2**15) != 0:
                        batFound = newdir
                        break
                elif validPath:
                    if newdir.lower()+".py" in curDLst_LC:
                        curDLst_indx = curDLst_LC.index(newdir.lower()+".py")
                        if os.stat(tmpDir+curDLst[curDLst_indx])[0] & (2**15) != 0:
                            exCmd(tmpDir+curDLst[curDLst_indx],passedIn)
                            cmdFound = True
                            break
                    elif newdir.lower()+".bat" in curDLst_LC:
                        curDLst_indx = curDLst_LC.index(newdir.lower()+".bat")
                        if os.stat(tmpDir+curDLst[curDLst_indx])[0] & (2**15) != 0:
                            batFound = curDLst[curDLst_indx]
                            break

            if '_switches' in envVars.keys():
                envVars.pop('_switches')

            if batFound != "":
                if activeBAT:
                    BATfile.close()
                BATfile = open(tmpDir+batFound)
                activeBAT = True
                batEcho = True
                batLabels = readBATFile(BATfile)
                batLineNo = 0
            elif not cmdFound:
                print("Illegal command:",cmdLine.split(" ")[0])

            gc.collect()

PyDOS()
