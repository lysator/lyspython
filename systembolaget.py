#!/usr/bin/env python2
# -*- coding: Latin-1 -*-
# (C) 2001-2003 Kent Engstr�m. Released under the GNU GPL.

import sys
import string
import re
import cStringIO
import urllib
import getopt
import md5

try:
    from regexpmatcher import M, MS, MSDeH, MSet, MList, MLimit
except ImportError:
    sys.stderr.write("*"*72 + "\nYou need regexpmatcher.py, which is "
                     "available at the same place as\nsystembolaget.py\n" \
                     + "*"*72 + "\n")
    raise

# L�n

lanslista = [
    ("02", "Stockholms l�n"),
    ("03", "Uppsala l�n"),
    ("04", "S�dermanlands l�n"),
    ("05", "�sterg�tlands l�n"),
    ("06", "J�nk�pings l�n"),
    ("07", "Kronobergs l�n"),
    ("08", "Kalmar l�n"),
    ("09", "Gotlands l�n"),
    ("10", "Blekinge l�n"),
    ("11", "Sk�ne l�n"),
    ("13", "Hallands l�n"),
    ("14", "V�stra G�talands l�n"),
    ("17", "V�rmlands l�n"),
    ("18", "�rebro l�n"),
    ("19", "V�stmanlands l�n"),
    ("20", "Dalarnas l�n"),
    ("21", "G�vleborgs l�n"),
    ("22", "V�sternorrlands l�n"),
    ("23", "J�mtlands l�n"),
    ("24", "V�sterbottens l�n"),
    ("25", "Norrbottens l�n"),
    ]

def find_lan(text):
    res = []
    text = string.lower(text)
    for (kod, namn) in lanslista:
        if string.find(string.lower(namn), text) == 0:
            res.append(kod)
    if len(res) == 1:
        return res[0]
    else:
        return None

# Helper functions

def format_titled(title, text, title_size = 16, max_col = 78):
    list = string.split(text)
    left = title + ":"
    pos = 0
    res = []
    for word in list:
        # Check if we should go to next line
        # We always place at least one word per line, even if that overflows
        # the line!
        if pos > 0 and pos + 1 + len(word) > max_col:
            res.append("\n")
            pos = 0

        # Now place word after title or space
        if pos == 0:
            res.append(string.ljust(left, title_size)[:title_size])
            left = ""
            pos = title_size
        else:
            res.append(" ")
            pos = pos + 1
        res.append(word)
        pos = pos + len(word)
    res.append("\n")
    return string.join(res, "")

def format_titled_fixed(title, text_lines, title_size = 16, max_col = 78):
    left = title + ":"
    res = []
    for line in text_lines:
        res.append("%-*s%s\n" %( title_size, left, line))
        left = ""
    return string.join(res, "")
    
def add_field(f, dict, title, key):
    if dict.has_key(key):
        f.write(format_titled(title, dict[key]))

def add_field_new(f, title, data):
    if data is not None:
        f.write(format_titled(title, data))

def add_to_list_from_dict(list, dict, key, fun = None):
    if dict.has_key(key):
        data = dict[key]
        if fun:
            data = fun(data)
        list.append(data)

def add_to_list_new(list, data, fun = None):
    if data is not None:
        if fun:
            data = fun(data)
        list.append(data)

def move_year_to_front(name):
    m = re.match(".*([12][90][0-9][0-9])$", name)
    if m:
        name = m.group(1) + " " + string.strip(name[:-4])
    return name

def left_zero_pad(str, minsize):
    return ("0"*minsize + str)[-minsize:]

def varu_url(prod_no):
    return "http://www.systembolaget.se/pris/owa/xdisplay?p_varunr=" + \
           prod_no

def klock_argument(s):
    # Parse number or range into min-max tuple
    try:
        (smin,smax) = string.split(s, "-")
    except ValueError:
        single = int(s)
        return (single, single)

    if smin == "":
        return (0,int(smax))
    elif smax== "":
        return (int(smin), 12)
    else:
        return (int(smin), int(smax))

# A helper class to make debugging easier and faster by caching
# webpages and storing them if WEBPAGE_DEBUG is true.
# This is only for debugging, as there is no code to handle GC
# nor to check for out-of-data information.

WEBPAGE_DEBUG = 0

class WebCache:
    def __init__(self):
        pass

    def filename(self, url):
        return "SYSTEMBOLAGET_" + md5.md5(url).hexdigest()
        
    def cached(self, url):
        if not WEBPAGE_DEBUG: return None
        try:
            f = open(self.filename(url))
            if WEBPAGE_DEBUG > 1: print "WP CACHED", url
            return f.read()
        except IOError:
            return None
        
    def cache(self, url, data):
        if not WEBPAGE_DEBUG: return None
        f = open(self.filename(url), "w")
        f.write(data)
        f.close()
        if WEBPAGE_DEBUG > 1: print "WP NEW", url
        
    def get(self, url): 
        cached = self.cached(url)
        if cached:
            return cached

        u = urllib.urlopen(url)
        data = u.read()
        u.close()

        self.cache(url, data)
        return data
       
The_WebCache = WebCache()

class WebPage:
    def __init__(self, url):
        self.url = url
        
    def get(self):
        return The_WebCache.get(self.url)
        
# Classes matching a single piece of data

class MSF(MS):
    def elaborate_pattern(self, pattern):
        return r"<B>%s</B></td>\n<td valign=top>(.*)</td></tr>" % pattern

class MSC(MS):
    def elaborate_pattern(self, pattern):
        return r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif" alt="[^"]*"><br> *%s *</center></td>' % pattern


class MSVolym(MS):
    def clean(self, data):
        # Things to clean up: spaces around the data
        # No space, or more than one space between digits and "ml"
        return string.join(string.split(string.strip(string.replace(data, "ml", " ml"))), " ")
# Bl�f�rgade artiklar finns i alla butiker
class MSAllaB(MS):
    def clean(self, data):
        if data == "0000FF":
            return "Ja"
        else:
            return "Nej"


# Object validity

(NEW, VALID, INVALID) = range(0,3)

# Product class

class Product:
    def __init__(self):
        self.state = NEW
        self.butiker = []
        
    # Parse the product page
    def from_html_normal(self, webpage):
        assert self.state == NEW

        self.grupp = MSDeH(r"<tr><td width=144> </td><td>\n(.+)\n").get(webpage)
        self.namn = MS(r"<b>([^(]+)\(nr [^)]*\)").get(webpage)
        self.varunr = MS(r"\(nr ([^)]*)\)").get(webpage)
        self.ursprung = MSF("Ursprung").get(webpage)
        self.producent = MSF("Producent").get(webpage)

        if self.namn and self.varunr:
            self.state = VALID
        else:
            self.state = INVALID
            return self
        
        self.forpackningar = []
        for f in MLimit(r'(?s)<td><table border="0" cellspacing="3">(.*?)</table></td></tr>', \
                        MList("<tr>",
                              M())).get(webpage):
            c = Container().from_html_normal(f)
            self.forpackningar.append(c)

        self.farg = MSF("F�rg").get(webpage)
        self.doft = MSF("Doft").get(webpage)
        self.smak = MSF("Smak").get(webpage)

        self.sotma = MSC("S�tma", advance = 0).get(webpage)
        self.fyllighet = MSC("Fyllighet", advance = 0).get(webpage)
        self.stravhet = MSC("Str�vhet", advance = 0).get(webpage)
        self.fruktsyra = MSC("Fruktsyra", advance = 0).get(webpage)
        self.beska = MSC("Beska", advance = 0).get(webpage)

        self.anvandning = MSF("Anv�ndning").get(webpage)
        self.hallbarhet = MSF("H�llbarhet").get(webpage)
        self.druvsorter = MSF("Druvsorter/R�varor").get(webpage)
        self.argang = MSF("Provad �rg�ng").get(webpage)
        self.provningsdatum = MSF("Provningsdatum").get(webpage)
        self.alkoholhalt = MS("<B>Alkoholhalt</B></td>\n<td valign=top>(.*)</td></tr>").get(webpage)

        return self

    # Parse the product information in a name or group search result.
    # We use separate regexps for the two cases in the specific
    # methods below; this functions should not be called directly.
    def from_html_productlist_common(self, webfragment, grupp, matcher):
        assert self.state == NEW

        dict = matcher.get(webfragment)
        
        self.grupp = grupp
        self.varunr = dict.get("varunr")
        self.namn = dict.get("namn")
        self.ursprung = dict.get("land")
        self.argang = dict.get("�rg�ng")
        
        if self.namn and self.varunr:
            self.state = VALID
        else:
            self.state = INVALID
            return self

        self.forpackningar = []
        for f in dict["f�rplista"]:
            c = Container().from_html_productlist(f)
            self.forpackningar.append(c)

        return self

    # Parse the product information in a name search result
    def from_html_name(self, webfragment, grupp):
        m = MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                  ("namn", MS('<B>(.*?)</B>')),
                  ("�rg�ng", MSDeH(r'<font [^>]*?>(.*?)</font>')),
                  ("varunr2", MS(r'<font [^>]*?>(.*?)</font>')),
                  ("land", MS(r'<font [^>]*?>(.*?)</font>')),
                  ("f�rplista",
                   MList(r'<font face="Arial, Helvetica, sans-serif" size="2">[0-9]+ml</font>',
                         M())),
                  ])
        return self.from_html_productlist_common(webfragment, grupp, m)
        

    # Parse the product information in a group search result
    def from_html_group(self, webfragment, grupp):
        m = MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                  ("namn", MS('<B>(.*?)</B>')),
                  ("�rg�ng", MSDeH(r'<font [^>]*?>([0-9]+|&nbsp;)<')),
                  ("varunr2", MS(r'<font [^>]*?>([0-9]+)<')),
                  ("land", MS(r'<font [^>]*?>(.*?)</font>')),
                  ("f�rplista",
                   MList(r'<font face="Arial, Helvetica, sans-serif" size="2">[0-9]+ ml',
                         M())),
                  ])
        return self.from_html_productlist_common(webfragment, grupp, m)

    # Parse the stores list for a product
    def from_html_stores(self, webpage, lan, ort):
        if lan <> "99":
            # Ett enda l�n
            self.butiker = []
            for b in MList(r'<tr><td width="200" valign=top>', M()).get(webpage):
                s = Store().from_html(b)
                if s.matches_ort(ort):
                    self.butiker.append(s)
        else:
            # En lista av l�n
            lista = MList("<H4>", MSet([("l�n", MS(r'<H4>(.*?)</H4>')),
                                         ("butikslista",
                                          MList(r'<tr><td width="200" valign=top>',
                                               M()))])).get(webpage)
            self.butiker = []
            for l in lista:
                lan = l["l�n"]
                for b in l["butikslista"]:
                    s = Store().from_html(b, lan)
                    if s.matches_ort(ort):
                        self.butiker.append(s)

    def valid(self):
        return self.state == VALID

    def typical_price(self):
        # Typical price, suitable for HTML display
        # Choose price for 700 or 750 ml if present, else first price.
        vald = None
        normala = ["750 ml", "700 ml"]
        for c in self.forpackningar:
            if vald is None or c.storlek in normala:
                vald = c

        pris = string.replace(string.replace(string.replace(vald.pris,
                                                            ".", ":"),
                                             ":00", ":-"),
                              " kr", "")
        
        if vald.storlek in normala:
            return pris
        else:
            storlek = string.replace(vald.storlek, "0 ml", " cl")
            return pris + " / " + storlek

    def to_string_stores(self):
        f = cStringIO.StringIO()
        tidigare_lan = None
        antal_lan = 0
        for butik in self.butiker:
            if butik.lan <> tidigare_lan:
                if antal_lan >0:
                    f.write("\n")
                f.write("%s\n\n" % butik.lan)
                tidigare_lan = butik.lan
                antal_lan = antal_lan + 1
                
            f.write(butik.to_string())
            
        return f.getvalue()

    def to_string_normal(self, butiker=0):
        f = cStringIO.StringIO()
        add_field_new(f, "Namn", self.namn)
        add_field_new(f, "Nr", self.varunr)
        add_field_new(f, "Grupp", self.grupp)
        add_field_new(f, "Ursprung", self.ursprung)
        add_field_new(f, "Producent", self.producent)
        add_field_new(f, "Druvsorter", self.druvsorter)
        f.write("\n")
        add_field_new(f, "F�rg", self.farg)
        add_field_new(f, "Doft", self.doft)
        add_field_new(f, "Smak", self.smak)
        f.write("\n")
        add_field_new(f, "S�tma", self.sotma)
        add_field_new(f, "Fyllighet", self.fyllighet)
        add_field_new(f, "Str�vhet", self.stravhet)
        add_field_new(f, "Fruktsyra", self.fruktsyra)
        add_field_new(f, "Beska", self.beska)
        f.write("\n")
        add_field_new(f, "Anv�ndning", self.anvandning)
        add_field_new(f, "H�llbarhet", self.hallbarhet)
        add_field_new(f, "Provad �rg�ng", self.argang)
        add_field_new(f, "Provad", self.provningsdatum)
        add_field_new(f, "Alkoholhalt", self.alkoholhalt)
        f.write("\n")

        f_lines = []
        for c in self.forpackningar:
            f_lines.append("%-18s %7s %7s %s %s" % (
                c.namn,
                c.storlek,
                c.pris,
                c.anm1,
                c.anm2))

        f.write(format_titled_fixed("F�rpackningar", f_lines))
        f.write("\n")
        f.write(format_titled("URL", self.url))

        if butiker:
            f.write("\n" + self.to_string_stores())
            
        return f.getvalue()

    def to_string_brief(self):
        f = cStringIO.StringIO()
        f.write("%s [%s]\n" %(move_year_to_front(self.namn),
                              self.varunr))
        lf = []
        add_to_list_new(lf, self.ursprung)
        add_to_list_new(lf, self.producent)
        add_to_list_new(lf, self.argang)
        add_to_list_new(lf, self.hallbarhet)
        f.write("      %s\n" % string.join(lf, ", "))
        lf = []
        for (kod, varde) in [("S�", self.sotma),
                             ("Fy", self.fyllighet),
                             ("St", self.stravhet),
                             ("Fr", self.fruktsyra),
                             ("Be", self.beska)]:
            kod = kod + ":"
            add_to_list_new(lf, varde, lambda x, kod = kod: kod + x)
        add_to_list_new(lf, self.alkoholhalt,
                        lambda x: string.replace(x, " volymprocent", "%"))
            
        for c in self.forpackningar:
            lf.append("%s/%s" % (c.pris, c.storlek))
        f.write("      %s\n" % string.join(lf, ", "))
        return f.getvalue()

    def clock_table(self):
        f = cStringIO.StringIO()
        f.write("<TABLE><TR>\n")
        for (namn, varde) in [("S�tma",     self.sotma),
                              ("Fyllighet", self.fyllighet),
                              ("Str�vhet",  self.stravhet),
                              ("Fruktsyra", self.fruktsyra),
                              ("Beska",     self.beska)]:
            if varde is not None:
                f.write("<TD><CENTER><IMG SRC=klock_%s.gif><BR>%s&nbsp;</CENTER></TD>\n" % (
                    varde, namn))
                
        f.write("</TR></TABLE>\n")
        return f.getvalue()
            
    def to_string_html(self,
                       include_sensory=1):
        f = cStringIO.StringIO()
        f.write('<TR><TD COLSPAN=2><B>%s (nr <a href=%s>%s</a>) %s</B></TD></TR>\n' % \
                (self.namn,
                 varu_url(self.varunr),
                 self.varunr,
                 self.typical_price()))

        f.write("<TR><TD>%s<BR>\n" % self.ursprung)
        if self.druvsorter is not None:
            f.write("%s<BR>\n" % self.druvsorter)
        f.write("%s</TD>\n" % string.replace(self.alkoholhalt, "volymprocent", "%"))

        f.write("<TD>%s</TD></TR>\n" % self.clock_table())

        if include_sensory:
            f.write("<TR><TD COLSPAN=2><UL>\n")
            for varde in [self.farg, self.doft, self.smak]:
                if varde is not None:
                    f.write("<LI>%s" % (varde))
            f.write("</UL></TD></TR>\n")
        
        f.write("<TR><TD COLSPAN=2>&nbsp;</TD></TR>\n")

        return f.getvalue()

    def to_string_productlist(self):
        f = cStringIO.StringIO()

        f.write("%7s  %s\n" % (self.varunr,
                               self.namn))
        fps = []
        for forp in self.forpackningar:
            fps.append(forp.to_string_productlist())

        f.write("         %4s %-32s %s\n" % (self.argang,
                                             self.ursprung,
                                             fps[0]))
        for fp in fps[1:]:
            f.write("                                               %s\n" % fp)
                    
        return f.getvalue()

    def search(self, prodno, butiker = 0, lan = None, ort = None):
        self.url = varu_url(str(prodno))

        # Product page
        webpage = WebPage(self.url).get()
        self.from_html_normal(webpage)

        # Stores
        if butiker:
            url = "http://www.systembolaget.se/pris/owa/zvselect?p_artspec=&p_varunummer=%s&p_lan=%s&p_back=&p_rest=0" % (prodno, lan)
            webpage = WebPage(url).get()
            self.from_html_stores(webpage, lan, ort)
            
        # The final touch
        return self

# Container class

class Container:
    def __init__(self):
        self.state = NEW
        
    # Parse the container information in a product page
    def from_html_normal(self, webfragment):
        assert self.state == NEW

        # We use this instead of inline field = Mfoo(...).get(webfragment)
        # as we believe the matches below need to be sequenced
        # just the way MSet does.
        dict = MSet([("namn", MS(r"<td>&#149; ([^<]+)</td>")),
                     ("storlek", MS(r"<td align=right>([^<]+)</td>")),
                     ("pris", MS(r"<td align=right>([^<]+)</td>")),
                     ("anm1", MSDeH(r"<td>(.*?)</td>")),
                     ("anm2", MSDeH(r"<td>(.+?)</td>")),
                     ]).get(webfragment)
        
        self.namn = dict.get("namn")
        self.storlek = dict.get("storlek")
        self.pris = dict.get("pris")
        self.anm1 = dict.get("anm1", "") 
        self.anm2 = dict.get("anm2", "")
        self.allabutiker = None # Does not know
        
        assert self.namn and self.storlek and self.pris
        self.state = VALID

        return self

    # Parse the container information in a name or group search result
    def from_html_productlist(self, webfragment):
        assert self.state == NEW

        dict = MSet([("volym", MSVolym(r'<font [^>]*?>(.*?)<')),
                     ("allabutiker", MSAllaB(r'<font [^>]*?color="#([0-9A-Fa-f]+)">')),
                     ("pris", MS(r'([0-9.]+ kr)')),
                     ]).get(webfragment)
        self.namn = None
        self.storlek = dict.get("volym")
        self.pris = dict.get("pris")
        self.anm1 = None
        self.anm2 = None
        self.allabutiker = dict.get("allabutiker")

        assert self.storlek and self.pris
        self.state = VALID

        return self

    def to_string_productlist(self):
        if self.allabutiker == "Ja":
            ab = " alla"
        else:
            ab = ""

        return "%11s (%s)%s" % (self.pris, self.storlek, ab)

    def valid(self):
        return self.state == VALID

# Store class

class Store:
    def __init__(self):
        self.state = NEW

    # Parse the store information in a store list item
    def from_html(self, webfragment, lan = None):
        assert self.state == NEW

        dict = MSet([("kod", MS(r'thebut=([0-9]+)')),
                     ("ort", MS(r'>(.*?)</a>')),
                     ("adress", MS(r'<td[^>]*>(.*?)</td>')),
                     ("telefon", MS(r'<td[^>]*>(.*?)</td>')),
                     ]).get(webfragment)

        self.lan = lan
        self.kod = dict.get("kod")
        self.ort = dict.get("ort")
        self.adress = dict.get("adress")
        self.telefon = dict.get("telefon")

        assert self.kod and self.ort and self.adress
        self.state = VALID

        return self
    
    def valid(self):
        return self.state == VALID

    def matches_ort(self, ort):
        if ort is None:
            return 1 # None matches all
        return self.ort.lower().find(ort.lower()) == 0
    
    def to_string(self):
        return "  %s, %s (%s) [kod %s]\n" % \
               (self.ort,
                self.adress,
                self.telefon,
                left_zero_pad(self.kod,4))


# ProductList class

(S_BOTH, S_ORD, S_BEST) = range(0,3)

class ProductList:
    def __init__(self):
        self.state = NEW
        
    # Parse the result of a name search 
    def from_html_name(self, webpage, ordinarie):
        assert self.state == NEW
        
        typlista = MList(r'<font face="TimesNewRoman, Arial, Helvetica, sans-serif" size="5">',
                         MSet([("typrubrik", MSDeH(r'<b>(.*?) *</b>')),
                               ("prodlista",
                                MList(r'<tr valign=top><td bgcolor="#[0-9a-fA-F]+" width=320>',
                                      M())),
                               ])).get(webpage)
        self.lista = []
        for t in typlista:
            grupp = t["typrubrik"]
            if not ordinarie:
                grupp = grupp + " (BEST�LLNINGSSORTIMENTET)"
            
            for p in t["prodlista"]:
                self.lista.append(Product().from_html_name(p, grupp))
            
        if self.lista:
            self.state = VALID
        else:
            self.state = INVALID
            
        return self
    
    # Parse the result of a group search 
    def from_html_group(self, webpage, ordinarie):
        assert self.state == NEW

        grupp = MSDeH(r'(?s)<font face="TimesNewRoman, Arial, Helvetica, sans-serif" size="5"><b>([<A-Z���].*?)</b>').get(webpage)
        if not ordinarie:
            grupp = grupp + " (BEST�LLNINGSSORTIMENTET)"
            
        prodlista = MList(r'<A HREF="xdisplay',
                          M()).get(webpage)
        
        self.lista = []
        for p in prodlista:
            self.lista.append(Product().from_html_group(p, grupp))
            
        if self.lista:
            self.state = VALID
        else:
            self.state = INVALID
            
        return self

    # Object validity
    def valid(self):
            return self.state == VALID

    # Merge this product list with another
    def merge(self, other):
        # FIXME: This is to naive for anything but ordinarie/best�llning
        # - It assumes that there is no overlap between lists
        # - It does not not reorder
        self.lista.extend(other.lista)
        if self.state == VALID or other.state == VALID:
            self.state = VALID # Superugly kludge
        
    # Replace the minimal Product object (from a name/group search)
    # with a full one (requires a web page fetch per product = expensive)
    def replace_with_full(self):
        l = []
        for p in self.lista:
            l.append(Product().search(p.varunr))
        self.lista = l

    def to_string(self, baravarunr = 0, fullstandig = 0, kort = 0):
        f = cStringIO.StringIO()

        if baravarunr:
            for p in self.lista:
                f.write("%s\n" % (p.varunr))
        else:
            tidigare_grupp = None

            for p in self.lista:
                grupp = p.grupp
                if grupp <> tidigare_grupp:
                    f.write(grupp + "\n\n")
                    tidigare_grupp = grupp

                if fullstandig:
                    f.write(p.to_string_normal())
                elif kort:
                    f.write(p.to_string_brief())
                else:
                    f.write(p.to_string_productlist())
                f.write("\n")

        return f.getvalue()

    def search_name(self, **args):
        # Argumentet sortiment: S_ORD, S_BEST, S_BOTH
        # ska �vers�ttas till "l�gniv�argumentet"
        # ordinarie=1, ordinarie=0 eller b�da!
        if args.has_key("sortiment"):
            sortiment = args["sortiment"]
            a = args.copy()
            del a["sortiment"]
            if sortiment == S_ORD:
                a["ordinarie"] = 1
                return self.search_name(**a)
            elif sortiment == S_BEST:
                a["ordinarie"] = 0
                return self.search_name(**a)
            else:
                # S�k f�rst i ordinarie (detta objekt)
                a["ordinarie"] = 1
                self.search_name(**a)
                # S�k sedan i best�llning (annat objekt)
                a["ordinarie"] = 0
                pl = ProductList()
                pl.search_name(**a)
                # S�tt ihop
                self.merge(pl)
                return self

        return self.search_name_internal(**args)

    def search_name_internal(self, namn, ordinarie):
        if ordinarie:
            p_ordinarie = "1"
        else:
            p_ordinarie = "0"
        url = "http://www.systembolaget.se/pris/owa/zname?p_namn=%s&p_wwwgrptxt=%%25&p_rest=0&p_soundex=0&p_ordinarie=%s" % (urllib.quote(namn), p_ordinarie)

        webpage = WebPage(url).get()
        self.from_html_name(webpage, ordinarie)

        return self

    def search_group(self, **args):
        # Argumentet sortiment: S_ORD, S_BEST, S_BOTH
        # ska �vers�ttas till "l�gniv�argumentet"
        # ordinarie=1, ordinarie=0 eller b�da!
        if args.has_key("sortiment"):
            sortiment = args["sortiment"]
            a = args.copy()
            del a["sortiment"]
            if sortiment == S_ORD:
                a["ordinarie"] = 1
                return self.search_group(**a)
            elif sortiment == S_BEST:
                a["ordinarie"] = 0
                return self.search_group(**a)
            else:
                # S�k f�rst i ordinarie (detta objekt)
                a["ordinarie"] = 1
                self.search_group(**a)
                # S�k sedan i best�llning (annat objekt)
                a["ordinarie"] = 0
                pl = ProductList()
                pl.search_group(**a)
                # S�tt ihop
                self.merge(pl)
                return self

        return self.search_group_internal(**args)
    
    
    def search_group_internal(self, grupp,
                              min_pris, max_pris,
                              ordinarie,
                              begr_butik,
                              forpackningstyp,
                              ekologiskt,
                              kosher,
                              nyhet,
                              varutyp,
                              ursprung,
                              p_klockor,
                              fat_karaktar,
                              ):
        if ordinarie:
            p_ordinarie = "1"
        else:
            p_ordinarie = "0"

        if begr_butik is None:
            begr_butik = "0"

        if forpackningstyp is None:
            p_type = "0"
        else:
            p_type = forpackningstyp                 

        if ekologiskt:
            p_eko = "&p_eko=yes"
        else:
            p_eko = ""

        if kosher:
            p_kosher = "&p_kosher=yes"
        else:
            p_kosher = ""

        if nyhet:
            p_nyhet = "&p_nyhet=yes"
        else:
            p_nyhet = ""

        if varutyp is None:
            p_varutyp = ""
        else:
            p_varutyp = urllib.quote(varutyp)

        if ursprung is None:
            p_ursprung = ""
        else:
            p_ursprung = urllib.quote(ursprung)

        grupp = urllib.quote(grupp)
        url = "http://www.systembolaget.se/pris/owa/sokpipe.sokpara?p_wwwgrp=%s&p_varutyp=%s&p_ursprung=%s&p_prismin=%s&p_prismax=%s&p_type=%s&p_kl_1_1=%d&p_kl_1_2=%d&p_kl_2_1=%d&p_kl_2_2=%d&p_kl_3_1=%d&p_kl_3_2=%d&p_kl_fat=%d%s%s%s&p_butnr=%s&p_ordinarie=%s&p_back=" % \
              (grupp, p_varutyp, p_ursprung,
               min_pris, max_pris,
               p_type,
               p_klockor[0][0],p_klockor[0][1],
               p_klockor[1][0],p_klockor[1][1],
               p_klockor[2][0],p_klockor[2][1],
               fat_karaktar,
               p_eko,
               p_kosher,
               p_nyhet,
               begr_butik, ordinarie)

        webpage = WebPage(url).get()
        self.from_html_group(webpage, ordinarie)

        return self
    
# COMMAND LINE OPERATION
def main():
    # Option handling
    
    debug = 0
    sortiment = S_BOTH
    kort = 0
    fullstandig = 0
    butiker = 0
    baravarunr = 0
    lan = "99"
    ort = None
    min_pris = 0
    max_pris = 1000000
    begr_butik = None
    grupp = None
    forpackningstyp = None
    ekologiskt = 0
    kosher = 0
    nyhet = 0
    varutyp = None
    ursprung = None
    p_klockor = [(0,0), (0,0) ,(0,0)]
    pos_fyllighet = None
    pos_stravhet = None
    pos_fruktsyra = None
    pos_sotma = None
    pos_beska = None
    fat_karaktar = 0
    
    F_HELP = 0
    F_NAMN = 1
    F_PRODUKT = 2
    F_VARA = 3
    
    funktion = F_HELP
    
    options, arguments = getopt.getopt(sys.argv[1:],
                                       "",
                                       ["debug",
                                        "namn=",
                                        "best�llningssortimentet",
                                        "ordinariesortimentet",
                                        "kort",
                                        "fullst�ndig",
                                        "butiker",
                                        "l�n=",
                                        "ort=",
    
                                        "r�da-viner",
                                        "vita-viner",
                                        "mousserande-viner",
                                        "ros�viner",
                                        "starkvin",
                                        "sprit",
                                        "�l",
                                        "cider",
                                        "blanddrycker",
                                        "alkoholfritt",
                                        
                                        "min-pris=",
                                        "max-pris=",
                                        "begr�nsa-butik=",
    
                                        "st�rre-flaskor",
                                        "helflaskor",
                                        "halvflaskor",
                                        "mindre-flaskor",
                                        "bag-in-box",
                                        "pappf�rpackningar",
                                        "burkar",
                                        "stora-burkar",
    
                                        "ekologiskt-odlat",
                                        "kosher",
                                        "nyheter",
                                        
                                        "varutyp=",
                                        "ursprung=",
    
                                        "fyllighet=",
                                        "str�vhet=",
                                        "fruktsyra=",
                                        "s�tma=",
                                        "beska=",
                                        
                                        "fat-karakt�r",
                                        "ej-fat-karakt�r",
    
                                        "bara-varunr",

                                        # Hidden
                                        "webpage-debug",
                                        ])
    
    for (opt, optarg) in options:
        if opt == "--debug":
            debug = 1
        elif opt == "--namn":
            funktion = F_NAMN
            namn = optarg
        elif opt == "--best�llningssortimentet":
            sortiment = S_BEST
        elif opt == "--ordinariesortimentet":
            sortiment = S_ORD
        elif opt == "--kort":
            kort = 1
        elif opt == "--fullst�ndig":
            fullstandig = 1
        elif opt == "--butiker":
            butiker = 1
        elif opt == "--l�n":
            butiker = 1
            kanske_lan = find_lan(optarg)
            if kanske_lan is not None:
                lan = kanske_lan
            else:
                sys.stderr.write("[L�n '%s' ej funnet --- ingen l�nsbegr�nsning.]\n" % optarg)
        elif opt == "--ort":
            butiker = 1
            ort = optarg
        elif opt == "--r�da-viner":
            funktion = F_PRODUKT
            grupp = "R�DA VINER"
            (pos_fyllighet, pos_stravhet, pos_fruktsyra) = range(0,3)
        elif opt == "--vita-viner":
            funktion = F_PRODUKT
            grupp = "VITA VINER"
            (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
        elif opt == "--ros�viner":
            funktion = F_PRODUKT
            grupp = "ROS�VINER"
            (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
        elif opt == "--mousserande-viner":
            funktion = F_PRODUKT
            grupp = "MOUSSERANDE VINER"
            (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
        elif opt == "--starkvin":
            funktion = F_PRODUKT
            grupp = "STARKVIN M. M."
        elif opt == "--sprit":
            funktion = F_PRODUKT
            grupp = "SPRIT"
        elif opt == "--�l":
            funktion = F_PRODUKT
            grupp = "�L"
            p_sotma_pos = 2
            (pos_beska, pos_fyllighet, pos_sotma) = range(0,3)
        elif opt == "--cider":
            funktion = F_PRODUKT
            grupp = "CIDER"
            (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
        elif opt == "--blanddrycker":
            funktion = F_PRODUKT
            grupp = "BLANDDRYCKER"
        elif opt == "--alkoholfritt":
            funktion = F_PRODUKT
            grupp = "ALKOHOLFRITT"
        elif opt == "--min-pris":
            min_pris = optarg
        elif opt == "--max-pris":
            max_pris = optarg
        elif opt == "--begr�nsa-butik":
            begr_butik = optarg
        elif opt == "--st�rre-flaskor":
            forpackningstyp = "2"
        elif opt == "--helflaskor":
            forpackningstyp = "5"
        elif opt == "--halvflaskor":
            forpackningstyp = "7"
        elif opt == "--mindre-flaskor":
            forpackningstyp = "1"
        elif opt == "--bag-in-box":
            forpackningstyp = "3"
        elif opt == "--pappf�rpackningar":
            forpackningstyp = "4"
        elif opt == "--burkar":
            forpackningstyp = "6"
        elif opt == "--stora-burkar":
            forpackningstyp = "9"
        elif opt == "--kosher":
            kosher = 1
        elif opt == "--ekologiskt-odlat":
            ekologiskt = 1
        elif opt == "--nyheter":
            nyhet = 1
        elif opt == "--varutyp":
            varutyp = optarg
        elif opt == "--ursprung":
            ursprung = optarg
        elif opt == "--fyllighet":
            p_klockor[pos_fyllighet] = klock_argument(optarg)
        elif opt == "--str�vhet":
            p_klockor[pos_stravhet] = klock_argument(optarg)
        elif opt == "--fruktsyra":
            p_klockor[pos_fruktsyra] = klock_argument(optarg)
        elif opt == "--s�tma":
            p_klockor[pos_sotma] = klock_argument(optarg)
        elif opt == "--beska":
            p_klockor[pos_beska] = klock_argument(optarg)
            
        elif opt == "--fat-karakt�r":
            fat_karaktar = 1
        elif opt == "--ej-fat-karakt�r":
            fat_karaktar = 2
        elif opt == "--bara-varunr":
            baravarunr = 1
        elif opt == "--webpage-debug":
            global WEBPAGE_DEBUG
            WEBPAGE_DEBUG = WEBPAGE_DEBUG + 1
        else:
            sys.stderr.write("Internt fel (%s ej behandlad)" % opt)
            sys.exit(1)
    
    if funktion == F_HELP and len(arguments) > 0:
        funktion = F_VARA
    
    if funktion == F_VARA:
        # Varufunktion
        for varunr in arguments:
            prod = Product().search(varunr, butiker, lan, ort)
            if prod.valid():
                if kort:
                    txt = prod.to_string_brief()
                else:
                    txt = prod.to_string_normal(butiker)
                print txt
            else:
                print "Varunummer %s verkar inte finnas." % varunr
                continue
            
    elif funktion == F_NAMN:
        # Namns�kning
        pl = ProductList().search_name(namn = namn,
                                      sortiment = sortiment)
        if pl.valid():
            if kort or fullstandig:
                pl.replace_with_full()
            print pl.to_string(baravarunr = baravarunr,
                               fullstandig = fullstandig,
                               kort = kort),
        else:
            print "S�kningen gav inga svar."
    
    elif funktion == F_PRODUKT:
        # Produkts�kning
        pl = ProductList().search_group(grupp = grupp,
                                        min_pris = min_pris,
                                        max_pris = max_pris,
                                        sortiment = sortiment,
                                        begr_butik = begr_butik,
                                        forpackningstyp = forpackningstyp,
                                        ekologiskt = ekologiskt,
                                        kosher = kosher,
                                        nyhet = nyhet,
                                        varutyp = varutyp,
                                        ursprung = ursprung,
                                        p_klockor = p_klockor,
                                        fat_karaktar = fat_karaktar,
                                        )
        if pl.valid():
            if kort or fullstandig:
                pl.replace_with_full()
            print pl.to_string(baravarunr = baravarunr,
                               fullstandig = fullstandig,
                               kort = kort),
        else:
            print "S�kningen gav inga svar."
    
    else: # F_HELP
        print "systembolaget.py --- kommandoradss�kning i Systembolagets katalog"
        print "-----------------------------------------------------------------"
        print 
        print "Varuvisning (med m�jlighet att visa butiker som har varan):"
        print """
       %s [--kort] [--butiker]
       %s [--l�n=L�N] [--ort=ORT]
       %s VARUNR...
    """ % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*2)
        print "Namns�kning:"
        print """
       %s [{--best�llningssortimentet |
       %s   --ordinariesortimentet}]
       %s [{--bara-varunr | --kort | --fullst�ndig}]
       %s  --namn=NAMN
    """ % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*3)
        print "Produkts�kning:"
        print """
       %s { --r�da-viner    | --vita-viner        |
       %s   --ros�viner     | --mousserande-viner |
       %s   --starkvin      | --sprit             |
       %s   --�l            | --cider             |
       %s   --blanddrycker  | --alkoholfritt }
       %s [{--best�llningssortimentet |
       %s   --ordinariesortimentet}]
       %s [--min-pris=MIN] [--max-pris=MAX]
       %s [{ --st�rre-flaskor | --mindre-flaskor |
       %s    --helflaskor     | --halvflaskor |
       %s    --bag-in-box     | --pappf�rpackningar |
       %s    --burkar         | --stora-burkar}]
       %s [{--ekologiskt-odlat | --kosher | --nyheter}
       %s [--varutyp=EXAKT-TYP]
       %s [--ursprung=EXAKT-LAND/REGION]
       %s [--begr�nsa-butik=BUTIKSKOD]
       %s [{--fyllighet=N | --str�vhet=N | --fruktsyra=N |
       %s   --s�tma=N     | --beska=N}]
       %s [{--fat-karakt�r | --ej-fat-karakt�r}]
       %s [{--bara-varunr | --kort | --fullst�ndig}]
    """ % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*19)


if __name__ == '__main__':
    main()
    
