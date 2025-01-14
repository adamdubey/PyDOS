import os, sys
from flashbdev import FlashBdev
from machine import SPI, Pin

spi=SPI(0, sck="FLASH_SCK", mosi="FLASH_MOSI", miso="FLASH_MISO", baudrate=24_000_000)
cs = Pin("FLASH_CS", Pin.OUT, value=1)

flash=FlashBdev(spi, cs)
try:
    vfs = os.VfsLfs1(flash, progsize=256)
except OSError as e:
    os.VfsLfs1.mkfs(flash, progsize=256)
    vfs = os.VfsLfs1(flash, progsize=256)

if "PyBasic" in os.listdir("/"):
    os.rename("/PyBasic","/_TmpBasic")

os.mount(vfs, "/PyBasic")

if "_TmpBasic" in os.listdir("/"):

    def filecpy(file1,file2):
        with open(file2, "wb") as fCopy:
            with open(file1, 'rb') as fOrig:
                for line in fOrig:
                    fCopy.write(line)
        return

    def dirMove(src,dst):
    # Assume src,dst are valid directories and full path from root

        try:
            os.mkdir(dst)
        except:
            pass

        os.chdir(src)
        for aFile in os.listdir():
            os.chdir(src)
            #print(aFile)
            print(".",end="")
            if os.stat(aFile)[0] & (2**15) != 0:
                filecpy(src+"/"+aFile,dst+"/"+aFile)
                os.remove(aFile)
            else:
                dirMove(src+"/"+aFile,dst+"/"+aFile)
                os.chdir(src)
                #print("in ",os.getcwd()," deleting ",aFile)
                os.rmdir(aFile)

    print("Moving /PyBasic files to secondary FLASH volume",end="")
    dirMove("/_TmpBasic","/PyBasic")
    print()
    os.chdir("/")
    os.rmdir("/_TmpBasic")
