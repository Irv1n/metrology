# xDevs.com test application for Fluke 5720A, v0.0

import sys
import time
import Gpib
import signal

dmm_val = 1.0
mfc_sv = 0.0  # Set point on MFC
mfc_pv = 0.0  # Measured point on MFC
dmm_temp = 37.5
mfc_isr = 0  # MFC's status register
refcal = 10.0000000
series1 = 2  # Some commands for series 2 may not be compatible with series 1


class Timeout():
    """Timeout class using ALARM signal"""

    class Timeout(Exception):
        pass

    def __init__(self, sec):
        self.sec = sec

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.sec)

    def __exit__(self, *args):
        signal.alarm(0)  # disable alarm

    def raise_timeout(self, *args):
        raise Timeout.Timeout()


class mfc():
    global mfc_sv
    global mfc_pv
    data = ""
    temp = 36.6
    cnti = 12

    def __init__(self, gpib, refcal, name):
        self.gpib = gpib
        self.inst = Gpib.Gpib(0, self.gpib, timeout=60)  # 5700A GPIB Address = self.gpib
        self.refcal = refcal
        self.name = name
        self.init_inst()

    def init_inst(self):
        # Setup Fluke 5700A
        self.inst.write("*CLS")
        self.inst.write("*ESR?")
        time.sleep(2)  # Take a nap for 2 sec

    def out_set(self, cmd):
        self.inst.write("OUT %s" % cmd)

    def out_enable(self):
        self.inst.write("OPER")

    def out_disable(self):
        self.inst.write("STBY")

    def read_isr(self):
        global mfc_isr
        self.inst.write("ISR?")
        mfc_isr = int(self.inst.read())

    def read_data(self, cmd):
        data_float = 0.0
        data_str = ""
        self.inst.write(cmd)

        try:
            with Timeout(20):
                data_str = self.inst.read()
        except Timeout.Timeout:
            print("Timeout exception from dmm %s on read_data() inst.read()\n" % self.name)
            return 0, float(0)
        # print ("Reading from dmm %s = %s" % (self.name,data_str))
        try:
            data_float = float(data_str)
        except ValueError:
            print("Exception thrown by dmm %s on read_data() - ValueError = %s\n" % (self.name, data_str))
            return 0, float(0)  # Exception on float conversion, 0 = error
        return 1, data_float  # Good read, 1 = converted to float w/o exception

    def get_temp(self):
        global dmm_temp
        print("Reading DMM temp")
        self.inst.write("TARM SGL,1")
        self.temp_status_flag, temp = self.read_data("TEMP?")
        if self.temp_status_flag:
            self.temp = temp
        dmm_temp = 37.5
        return self.temp

    def out_read(self):
        global mfc_pv
        temp_str = self.inst.read()
        self.inst.write("OUT?")
        tmp_str = self.inst.read()
        parse_str = tmp_str.split(",")
        try:
            mfc_pv = float(parse_str[0])
        except ValueError:
            print("Exception thrown by MFC on read_data - ValueError = %s\n" % mfc_pv)

    def get_temp_status(self):
        return self.temp_status_flag

    def get_data(self):
        global dmm_val
        self.status_flag, data = self.read_data("TARM SGL,1")
        if self.status_flag:
            self.data = data
            dmm_val = float(data)
            self.ppm = ((float(self.data) / self.refhp) - 1) * 1E6
        return self.data

    def get_data_status(self):
        return self.status_flag


class dmm():
    global dmm_val
    data = ""
    temp = 36.6
    cnti = 12

    def __init__(self, gpib, refhp, name):
        self.gpib = gpib
        self.inst = Gpib.Gpib(0, self.gpib, timeout=60)  # 3458A GPIB Address = self.gpib
        self.refhp = refhp
        self.name = name
        self.init_inst()

    def init_inst(self):
        # Setup HP 3458A
        self.inst.write("PRESET NORM")
        self.inst.write("OFORMAT ASCII")
        self.inst.write("FUNC DCV,AUTO")
        self.inst.write("NPLC 100")
        self.inst.write("NDIG 9")
        self.inst.write("TARM HOLD")
        self.inst.write("AZERO ON")
        self.inst.write("NRDGS 1,AUTO")
        self.inst.write("TRIG LINE")
        self.inst.write("MEM OFF")
        self.inst.write("END ALWAYS")

    def switch_dci(self):
        self.inst.write("PRESET NORM")
        self.inst.write("FUNC DCI,AUTO")
        self.inst.write("NPLC 100")
        self.inst.write("NDIG 9")
        self.inst.write("AZERO ON")
        self.inst.write("NRDGS 1,AUTO")
        self.inst.write("OFORMAT ASCII")

    def read_data(self, cmd):
        data_float = 0.0
        data_str = ""
        self.inst.write(cmd)

        try:
            with Timeout(20):
                data_str = self.inst.read()
        except Timeout.Timeout:
            print("Timeout exception from dmm %s on read_data() inst.read()\n" % self.name)
            return 0, float(0)
        # print ("Reading from dmm %s = %s" % (self.name,data_str))
        try:
            data_float = float(data_str)
        except ValueError:
            print("Exception thrown by dmm %s on read_data() - ValueError = %s\n" % (self.name, data_str))
            return 0, float(0)  # Exception on float conversion, 0 = error
        return 1, data_float  # Good read, 1 = converted to float w/o exception

    def get_temp(self):
        global dmm_temp
        print("Reading DMM temp")
        self.inst.write("TARM SGL,1")
        self.temp_status_flag, temp = self.read_data("TEMP?")
        if self.temp_status_flag:
            self.temp = temp
        dmm_temp = 37.5
        return self.temp

    def get_temp_status(self):
        return self.temp_status_flag

    def get_data(self):
        global dmm_val
        self.status_flag, data = self.read_data("TARM SGL,1")
        if self.status_flag:
            self.data = data
            dmm_val = float(data)
            self.ppm = ((float(self.data) / self.refhp) - 1) * 1E6
        return self.data

    def exec_acal(self):
        sys.stdout.write("\033[1;35mACAL ALL procedure start, please wait 14 minutes ")
        self.inst.write("ACAL ALL")
        for cnt in range(0, 52):  # wait 840 seconds, print dot every 15s
            sys.stdout.write("\033[0;43m*")
            time.sleep(15)
        print("\r\nACAL procedure done...\033[1;39m")

    def exec_idn(self):
        self.inst.write("END ALWAYS")
        self.inst.write("ID?")
        dat = self.inst.read()
        tstr = dat.split()
        if tstr[0] == "HP3458A":
            sys.stdout.write("\r\n\033[1;32m%s detected...\033[1;39m" % tstr[0])
        else:
            sys.stdout.write("\r\n\033[1;31mNo DMM present, exiting!\033[1;39m")
            quit()

    def get_data_status(self):
        return self.status_flag


with open('testlog_5700a.txt', 'wb') as b:
    uut = mfc(4, refcal, "MFC")  # Fluke 5720A under test GPIB address init 1
    uut.inst.clear()

    uut_idn = "FLUKE"
    uut_mdl = "5720A"
    cnt = 0
    samples = 0
    val = 3.423
    temp = 36.6

    sys.stdout.write("\033[0;36m Fluke 5720A initial test tool \r\n  Using NI GPIB adapter with next instruments "
                     "config: \r\n * GPIB 4 : Fluke 5720A UUT \r\n * GPIB 22 : HP 3458A 8.5-digit DMM \r\n ! Do not "
                     "swap terminals during calibration, high voltage may be present !\033[0;39m\r\n\r\n")

    uut.inst.write("*IDN?")
    idn_str = uut.inst.read()
    idmfg = idn_str.split(",")
    if uut_idn == idmfg[0]:
        if uut_mdl == idmfg[1]:
            sys.stdout.write("\033[0;32mFluke 5720A detected, S/N %s, Version: %s\033[0;39m\r\n" % (idmfg[2], idmfg[3]))
            b.write("\r\nFluke 5720A - detected, S/N %s, Version: %s\r\n" % (idmfg[2], idmfg[3]))
        else:
            print("\033[0;31mIncorrect Model! Check GPIB address. Testing abort.\033[0;39m")
            quit()
    else:
        sys.stdout.write("\033[0;31mNo Fluke 5720A instrument detected. Check GPIB address. Testing abort.\033[0;39m")
        quit()

    if int(idmfg[2]) < 6565601:
        print("This is Series I unit")
        b.write("This is Series I unit\r\n")
    else:
        series1 = 0
        print("This is Series II unit")
        b.write("This is Series II unit\r\n")

    # Fluke 5720A MFC present, proceed with initial config

    uut.init_inst()
    uut.out_disable()
    time.sleep(1)  # take short nap
    uut.inst.write("FAULT?")
    flt = int(uut.inst.read())
    if int(flt) == 0:
        print("No GPIB data faults, we good to go")
        b.write("Calibrator reported no GPIB faults\r\n")

    # Configure MFC's serial port, 19200 8N1, CRLF EOF

    print("-i- Reading initial calibration data from 5720A")
    b.write("-i- Reading initial calibration data from 5720A\r\n")

    #    uut.inst.write ("SP_SET 19200,TERM,XON,DBIT8,SBIT1,PNONE,CRLF")
    #    uut.inst.read()
    #    print("Reading last calibration data\r\n")
    #    uut.inst.write ("CAL_PR CAL")                           # Printout last calibration data
    #    time.sleep(20)                                          # Take a nap for 20 seconds
    #    print("Reading last calibration check data\r\n")
    #    uut.inst.write ("CAL_PR CHECK")                         # Printout last calibration check data
    #    time.sleep(20)                                          # Take a nap for 20 seconds
    #    print("Reading raw goodies!\r\n")
    #    uut.inst.write ("CAL_PR RAW")                           # Printout RAW goodies
    #    time.sleep(20)                                          # Take a nap for 20 seconds

    # in future let's use CAL_RPT? and CAL_CLST? commands, which does same thing but over GPIB instead of serial.
    # this covered in OM PDF at page 171
    print("Reading cal days\r\n")
    uut.inst.write("CAL_DAYS? CAL")
    temp_str = int(uut.inst.read())
    print("Unit last calibrated : %d days ago" % temp_str)
    b.write("Unit last calibrated : %d days ago\r\n" % temp_str)

    if series1 == 0:
        uut.inst.write("CAL_CONF?")
        temp_str = uut.inst.read()
        print("Unit calibration confidence level : %s" % temp_str)
        b.write("Unit calibration confidence level : %s\r\n" % temp_str)

    uut.inst.write("ETIME?")
    lifetime = int(uut.inst.read())
    print("Unit running time : %d hr" % (lifetime / 60))
    b.write("Unit running time : %d hr\r\n" % (lifetime / 60))

    uut.inst.write("CAL_CONST? CHECK, KV6")
    rd_const = uut.inst.read()
    print("CAL CONST 6.5V reference voltage : %s" % rd_const)
    b.write("CAL CONST 6.5V reference voltage : %s\r\n" % rd_const)

    uut.inst.write("CAL_CONST? CHECK, KV13")
    rd_const = uut.inst.read()
    print("CAL CONST 13V reference voltage : %s" % rd_const)
    b.write("CAL CONST 13V reference voltage : %s\r\n" % rd_const)

    uut.inst.write("CAL_CONST? CHECK, RS10K")
    rd_const = uut.inst.read()
    print("CAL CONST 10KOHM standard resistance : %s" % rd_const)
    b.write("CAL CONST 10KOHM standard resistance : %s\r\n" % rd_const)

    uut.inst.write("CAL_CONST? CHECK, ZERO_TEMP")
    rd_const = uut.inst.read()
    print("CAL CONST, Zero calibration temperature : %s" % rd_const)
    b.write("CAL CONST, Zero calibration temperature : %s\r\n" % rd_const)

    uut.inst.write("CAL_CONST? CHECK, ALL_TEMP")
    rd_const = uut.inst.read()
    print("CAL CONST, All calibration temp : %s" % rd_const)
    b.write("CAL CONST, All calibration temp : %s\r\n" % rd_const)

    uut.read_isr()
    if mfc_isr & 0x0001:
        print("Calibrator output OPERATING")
        b.inst.write("Calibrator output OPERATING\r\n")
    if mfc_isr & 0x0002:
        print("Calibrator EXT GUARD enabled")
        b.inst.write("Calibrator EXT GUARD enabled\r\n")
    if mfc_isr & 0x0004:
        print("Calibrator EXT SENSE enabled")
        b.write("Calibrator EXT SENSE enabled\r\n")
    if mfc_isr & 0x0008:
        print("Calibrator BOOST (auxilary amp) enabled")
        b.write("Calibrator BOOST (auxilary amp) enabled\r\n")
    if mfc_isr & 0x0010:
        print("Calibrator 2-wire RCOMP enabled")
        b.write("Calibrator 2-wire RCOMP enabled\r\n")
    if mfc_isr & 0x0020:
        print("Calibrator output range is LOCKED")
        b.write("Calibrator output range is LOCKED\r\n")
    if mfc_isr & 0x0040:
        print("Calibrator variable phase is active")
        b.write("Calibrator variable phase is active\r\n")
    if mfc_isr & 0x0080:
        print("Calibrator output PLL LOCKED to EXT SOURCE")
        b.write("Calibrator output PLL LOCKED to EXT SOURCE\r\n")
    if mfc_isr & 0x0100:
        print("Calibrator OFFSET active")
        b.write("Calibrator OFFSET active\r\n")
    if mfc_isr & 0x0200:
        print("Calibrator SCALE active")
        b.write("Calibrator SCALE active\r\n")
    if mfc_isr & 0x0400:
        print("Calibrator WIDEBAND active")
        b.write("Calibrator WIDEBAND active\r\n")
    if mfc_isr & 0x0800:
        print("Calibrator UNDER REMOTE CONTROL")
        b.write("Calibrator UNDER REMOTE CONTROL\r\n")
    if mfc_isr & 0x1000:
        print("Calibrator STABLE (settled within spec)")
        b.write("Calibrator STABLE (settled within spec)\r\n")
    if mfc_isr & 0x2000:
        print("Calibrator is cooking report over SERIAL")
        b.write("Calibrator is cooking report over SERIAL\r\n")

    uut.inst.write("*PUD?")
    pud_str = uut.inst.read()
    print("User string PUD : %s" % pud_str)
    b.write("User string PUD : %s\r\n" % pud_str)

    # for cnt in range (0, 10):
    # Need check if this command works correctly. So far it just try to read 10 times fatality errors history
    uut.inst.write("FATALITY?")
    ferr_str = uut.inst.read()
    print("Fatal errors history: %s" % ferr_str)
    b.write("Fatal errors history: %s\r\n" % ferr_str)
    #    ferr_str = uut.inst.read()
    #    b.write("%s" % ferr_str)

    print("\033[1;31mConnect 3458A DCV volts input to Fluke 5720A HI/LO output jacks.\033[1;39m")
    raw_input("\033[1;33mPress Enter to continue with test...\033[1;39m")

    # F5720 data read OK. Detect HP 3458A DMM on GPIB 3
    dmm = dmm(22, dmm_val, "3458A")  # GPIB 3
    dmm.exec_idn()
    dmm.get_temp()
    dmm.inst.clear()
    print("\033[0;33mHP3458A TEMP = %2.1f C\033[0;33m" % dmm_temp)
    b.write("HP 3458A detected\r\n TEMP? = %2.1f C\r\n" % dmm_temp)

    # dmm.exec_acal()                                         # Execute ACAL on HP 3458A for best accuracy. Takes 14
    # minutes to complete.

    sys.stdout.write("\r\n\r\n5720A Performance test\r\n")
    dmm.init_inst()
    dmm.get_temp()
    sys.stdout.write("3458A TEMP? = %02.1f \r\n" % dmm_temp)

    print("So far just quick 10V output check")
    uut.out_set("10V")  # program 10V and enable output
    uut.out_enable()
    uut.inst.write("*WAI; OUT?")  # Wait for output to settle and read output
    time.sleep(2)  # take a nap few seconds
    uut.out_read()
    print("Fluke 5720A readback output = %12.9f V" % mfc_pv)
    b.write("Fluke 5720A readback output = %12.9f V\r\n" % mfc_pv)

    # for cnt in range (0, len(test_dcv_set)):
    #    uut.write (":SOUR:FUNC VOLT")
    #    uut.write (":SENS:CURR:PROT 0.1")
    #    uut.write (":SENS:CURR:RANG 0.1")
    #    uut.write (":OUTP:STAT ON")
    #    time.sleep(1)
    #    uut.write (":SOUR:VOLT:RANGE %3.1e" % test_dcv_rng[cnt])
    #    uut.write (":SOUR:VOLT %3.1e" % test_dcv_set[cnt])
    #    time.sleep(1)

    val = 0
    for samples in range(0, 5):
        dmm.get_data()
        print("Test DCV %d : %.9E VDC" % (samples, dmm_val))
        val += dmm_val
    val = val / 5
    ppm = ((val / 10.00) - 1) * 1E6

    # sys.stdout.write(" Verification step  %02d (%.9E) : %.9E VDC [deviation %6.2f ppm]\r\n" % (cnt, test_dcv_set[
    # cnt], val, ppm)) b.write("DCV Verification step %02d (%.9E), measured : %.9E VDC, deviation %.3f ppm\r\n" % (
    # cnt, test_dcv_set[cnt], val, ppm))
    sys.stdout.write("10V test result: %.9E VDC [deviation %6.4f ppm]\r\n" % (val, ppm))
    b.write("10V test result: %.9E VDC [deviation %6.4f ppm]\r\n" % (val, ppm))
    # cnt = cnt + 1

    uut.out_disable()
    uut.inst.write("LOCAL")  # bring 5720A to local operation
    dmm.inst.write("LOCAL")  # bring 3458A to local operation

    b.write("Program completed!")
    b.close()
