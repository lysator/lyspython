# Date class for Python
# Copyright 1997 Signum Support AB.
# Released under the GNU GPL.

import time
import string
import regex

#
# AUXILIARY ROUTINES
#
# Most important algorithms are from:
# Meeus, Jean, Astronomical Formulae for Calculators, 2 ed
#

# Convert JD -> YMD

def jd_to_ymd(jd):
    alpha = int((100*jd - 186721625L)/3652425L)
    a = jd + 1 + alpha - alpha/4
    b = a + 1524
    c = int(100*b - 12210)/36525
    d = int((36525L*c)/100)
    e = int((10000L*b-10000L*d)/306001L)
    res_d = b - d - int((306001L*e)/10000L)
    if e<14:
	res_m=e-1
    else:
	res_m=e-13
    if res_m<3:
	res_y=c-4715
    else:
	res_y=c-4716

    return (res_y,res_m,res_d)

# Convert YMD -> JD 

def ymd_to_jd(y,m,d):
    if m<3: y=y-1; m=m+12
    a = y/100;
    return 1720995 + d + 2 - a + (a/4) + (36525*y)/100 + (306001*(m+1))/10000;

# Get weekday from JD (Monday = 1, ..., Sunday = 7)

def jd_to_weekday(jd):
    return jd%7+1

# Convert YMD -> YWD

def ymd_to_ywd(y,m,d):
     jd=ymd_to_jd(y,m,d)
     jd1jan=ymd_to_jd(y,1,1)

     wd1jan=jd_to_weekday(jd1jan)
     if wd1jan<=4:
	 jd1mon=jd1jan+1-wd1jan
     else:
	 jd1mon=jd1jan+8-wd1jan

     if jd<jd1mon:
	 res_y=y-1
	 if jd_to_weekday(ymd_to_jd(y-1,1,1))<=4:
	     res_w=53
	 else:
	     res_w=52
     else:
	 res_y=y
	 res_w=(jd-jd1mon)/7+1
	 if m==12 and d>=29:
	     wd1jannext=jd_to_weekday(ymd_to_jd(y+1,1,1))
	     if wd1jannext<=4 and wd1jannext+d>=33:
		 res_y=y+1
		 res_w=1

     return (res_y,res_w,jd_to_weekday(jd))

# Convert YWD -> JD

def ywd_to_jd(y,w,d):
    jd1jan = ymd_to_jd(y,1,1)
    wd1jan = jd_to_weekday(jd1jan)
    if wd1jan <= 4:
	jd1mon = jd1jan + 1 - wd1jan
    else:
	jd1mon = jd1jan + 8 - wd1jan;

    return jd1mon + w * 7 + d - 8


# Convert YWD -> YMD (internally via JD)

def ywd_to_ymd(y,w,d):
    return jd_to_ymd(ywd_to_jd(y,w,d))


#
# THE DATE CLASS
#

class Date:
    # Initializing and printing

    def __init__(self): # New instances should be invalid!
	self.__valid = 0

    def __repr__(self):
	if self.__valid:
	    return "<Date %04d-%02d-%02d>"%(self.__y, self.__m, self.__d)
	else:
	    return "<Date invalid>"

    # Setting the date in different formats

    def SetJD(self, jd): # Julian date
	if type(jd) == type(0):
	    (self.__y, self.__m, self.__d) = jd_to_ymd(jd)
	    self.__valid = 1
	else:
	    self.__valid = 0

    def SetYMD(self, y, m, d): # Year, month, date
	# Check this date by converting to JD and back.
	jd = ymd_to_jd(y, m, d)
	(y2, m2, d2) = jd_to_ymd(jd)
	if y == y2 and m == m2 and d == d2:
	    (self.__y, self.__m, self.__d) = (y, m, d)
	    self.__valid = 1
	else:
	    self.__valid = 0
	
    def SetYWD(self, y, w, d): # Year, week, (week)day
	(y2, m2, d2) = ywd_to_ymd(y, w, d)
	self.SetYMD(y2, m2, d2) 
	# Check validity by convering back to YWD
	if self.__valid:
	    (y3, w3, d3) = self.GetYWD()
	    if y3 <> y or w3 <> w or d3 <> d:
		self.__valid = 0

    # Getting (parts of) the date in different formats

    def GetJD(self): # Julian date
	if self.__valid:
	    return ymd_to_jd(self.__y, self.__m, self.__d)
	else:
	    raise ValueError

    def GetYMD(self): # Year, month, date
	if self.__valid:
	    return (self.__y, self.__m, self.__d)
	else:
	    raise ValueError

    def GetYWD(self): # Year, week, (week)day
	if self.__valid:
	    return ymd_to_ywd(self.__y, self.__m, self.__d)
	else:
	    raise ValueError

    # Getting some common string formats

    def GetString_YYYY_MM_DD(self):
	return "%04d-%02d-%02d"%(self.GetYMD())

    def GetString_YYYYMMDD(self):
	return "%04d%02d%02d"%(self.GetYMD())

    def GetString_YY_MM_DD(self):
	(y, m, d) = self.GetYMD()
	return "%02d-%02d-%02d"%(y % 100, m, d)

    def GetString_YYMMDD(self):
	(y, m, d) = self.GetYMD()
	return "%02d%02d%02d"%(y % 100, m, d)

    # Adding an integer: step that many days into the future

    def __add__(self, days):
	return FromJD(self.GetJD() + days)

    # Subtracting an integer: step that many days into the past
    # Subtracting two dates: get difference in days

    def __sub__(self, right):
	if type(right) == type(0):
	    return FromJD(self.GetJD() - days)
	else: 
	    return self.GetJD()-right.GetJD()

#
# INITIALIZERS FOR THE DATE CLASS
#
# These are the functions you should call to get new instances of
# the Date class

def FromJD(jd):
    newdate = Date()
    newdate.SetJD(jd)
    return newdate

def FromYMD(y, m, d):
    newdate = Date()
    newdate.SetYMD(y, m, d)
    return newdate

def FromYWD(y, w, d):
    newdate = Date()
    newdate.SetYWD(y, w, d)
    return newdate

def FromToday():
    (dy,dm,dd,th,tm,ts,wd,dayno,ds)=time.localtime(time.time())
    return FromYMD(dy,dm,dd)

rx_dashed=regex.compile("^\([0-9]+\)-\([0-9]+\)-\([0-9]+\)$")
rx_yyyymmdd=regex.compile("^\([0-9][0-9][0-9][0-9]\)\([0-9][0-9]\)\([0-9][0-9]\)$")
rx_yymmdd=regex.compile("^\([0-9][0-9]\)\([0-9][0-9]\)\([0-9][0-9]\)$")
    
def FromString(str):
    newdate = Date() # Allocates an invalid date
    if rx_dashed.search(str)<>-1: # FIXME: YY-MM-DD and Y2K?
	newdate.SetYMD(string.atoi(rx_dashed.group(1)),
		       string.atoi(rx_dashed.group(2)),
		       string.atoi(rx_dashed.group(3)))
    elif rx_yyyymmdd.search(str)<>-1:
	newdate.SetYMD(string.atoi(rx_yyyymmdd.group(1)),
		       string.atoi(rx_yyyymmdd.group(2)),
		       string.atoi(rx_yyyymmdd.group(3)))

    elif rx_yymmdd.search(str)<>-1: # FIXME: YYMMDD and Y2K?
	newdate.SetYMD(string.atoi(rx_yymmdd.group(1)),
		       string.atoi(rx_yymmdd.group(2)),
		       string.atoi(rx_yymmdd.group(3)))

    return newdate
