#!/usr/bin/env python

import sys
import string
import re
import cStringIO
import urllib
import getopt

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

def add_to_list_from_dict(list, dict, key, fun = None):
    if dict.has_key(key):
        data = dict[key]
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

# Classes matching a single piece of data

class MSF(MS):
    def elaborate_pattern(self, pattern):
        return r"<B>%s</B></td>\n<td valign=top>(.*)</td></tr>" % pattern

class MSC(MS):
    def elaborate_pattern(self, pattern):
        return r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif"\n><br> *%s *</center></td>' % pattern


class MSVolym(MS):
    def clean(self, data):
        return re.sub("ml", " ml",
                      string.join(string.split(string.strip(data)), " "))


# Product class

prod_m = MSet([("grupp", MS(r"<tr><td width=144> </td><td>\n(.+)\n")),
               ("namn", MS(r"<B>([^(]+)\(nr [^)]*\)")),
               ("varunr", MS(r"\(nr ([^)]*)\)")),
               ("ursprung",MSF("Ursprung")),
               ("producent",MSF("Producent")),
               ("f�rpackningar",
                MLimit(r'(?s)<td><table border=1><tr><td><table border=0>(.*?)</table></td></tr></table>',
                       MList("<tr>",
                             MSet([("namn", MS(r"<td>([^<]+)</td>")),
                                   ("storlek", MS(r"<td align=right>([^<]+)</td>")),
                                   ("pris", MS(r"<td align=right>([^<]+)</td>")),
                                   ("anm1", MS(r"<td>([^<]+)</td>")),
                                   ("anm2", MSDeH(r"<td>(.+?)</td>")),
                                   ])))), 
               ("f�rg",MSF("F�rg")),
               ("doft",MSF("Doft")),
               ("smak",MSF("Smak")),
               ("s�tma",MSC("S�tma", advance = 0)),
               ("fyllighet",MSC("Fyllighet", advance = 0)),
               ("str�vhet",MSC("Str�vhet", advance = 0)),
               ("fruktsyra",MSC("Fruktsyra", advance = 0)),
               ("beska",MSC("Beska", advance = 0)),
               ("anv�ndning",MSF("Anv�ndning")),
               ("h�llbarhet",MSF("H�llbarhet")),
               ("provad_�rg�ng",MSF("Provad �rg�ng")),
               ("provningsdatum",MSF("Provningsdatum")),
               ("alkoholhalt",MS("<B>Alkoholhalt</B></td>\n<td valign=top>(.*\n.*)</td></tr>")),
               ])    

class Product:
    def __init__(self, webpage):
        (self.dict, pos) = prod_m.match(webpage, 0, len(webpage))

    def valid(self):
        return self.dict.has_key("namn")

    def typical_price(self):
        # Typical price, suitable for HTML display
        # Choose price for 700 or 750 ml if present, else first price.
        vald = None
        normala = ["750 ml", "700 ml"]
        for f_dict in self.dict["f�rpackningar"]:
            if vald is None or f_dict.get("storlek")in normala:
                vald = f_dict

        pris = string.replace(string.replace(string.replace(vald["pris"],
                                                            ".", ":"),
                                             ":00", ":-"),
                              " kr", "")
        
        if vald["storlek"] in normala:
            return pris
        else:
            storlek = string.replace(vald["storlek"], "0 ml", " cl")
            return pris + " / " + storlek

    def clock_table(self):
        f = cStringIO.StringIO()
        f.write("<TABLE><TR>\n")
        for egenskap in ["s�tma","fyllighet", "str�vhet",
                         "fruktsyra", "beska"]:
            if self.dict.has_key(egenskap):
                f.write("<TD><CENTER><IMG SRC=klock_%s.gif><BR>%s&nbsp;</CENTER></TD>\n" % (
                    self.dict[egenskap],
                    string.capitalize(egenskap)))
        f.write("</TR></TABLE>\n")
        return f.getvalue()
            
    def to_string(self):
        f = cStringIO.StringIO()
        add_field(f, self.dict, "Namn","namn")
        add_field(f, self.dict, "Nr","varunr")
        add_field(f, self.dict, "Grupp","grupp")
        add_field(f, self.dict, "Ursprung","ursprung")
        add_field(f, self.dict, "Producent","producent")
        f.write("\n")
        add_field(f, self.dict, "F�rg","f�rg")
        add_field(f, self.dict, "Doft","doft")
        add_field(f, self.dict, "Smak","smak")
        f.write("\n")
        add_field(f, self.dict, "S�tma","s�tma")
        add_field(f, self.dict, "Fyllighet","fyllighet")
        add_field(f, self.dict, "Str�vhet","str�vhet")
        add_field(f, self.dict, "Fruktsyra","fruktsyra")
        add_field(f, self.dict, "Beska","beska")
        f.write("\n")
        add_field(f, self.dict, "Anv�ndning","anv�ndning")
        add_field(f, self.dict, "H�llbarhet","h�llbarhet")
        add_field(f, self.dict, "Provad �rg�ng","provad_�rg�ng")
        add_field(f, self.dict, "Provad","provningsdatum")
        add_field(f, self.dict, "Alkoholhalt","alkoholhalt")
        f.write("\n")

        f_lines = []
        for f_dict in self.dict["f�rpackningar"]:
            f_lines.append("%-18s %7s %7s %s %s" % (
                f_dict.get("namn"),
                f_dict.get("storlek"),
                f_dict.get("pris"),
                f_dict.get("anm1", ""),
                f_dict.get("anm2", "")))

        f.write(format_titled_fixed("F�rpackningar", f_lines))
        f.write("\n")
        f.write(format_titled("URL", self.url))

        return f.getvalue()

    def to_string_brief(self):
        f = cStringIO.StringIO()
        f.write("%s [%s]\n" %(move_year_to_front(self.dict["namn"]),
                              self.dict["varunr"]))
        lf = []
        add_to_list_from_dict(lf, self.dict, "ursprung")
        add_to_list_from_dict(lf, self.dict, "producent")
        add_to_list_from_dict(lf, self.dict, "provad_�rg�ng")
        add_to_list_from_dict(lf, self.dict, "h�llbarhet")
        f.write("      %s\n" % string.join(lf, ", "))
        lf = []
        for egenskap in ["s�tma","fyllighet","str�vhet","fruktsyra","beska"]:
            kod = string.capitalize(egenskap)[:2]+":"
            add_to_list_from_dict(lf, self.dict, egenskap,
                                  lambda x, kod = kod: kod + x)
        add_to_list_from_dict(lf, self.dict, "alkoholhalt",
                              lambda x: string.replace(x, " volymprocent", "%"))
            
        for f_dict in self.dict["f�rpackningar"]:
            lf.append("%s/%s" % (f_dict.get("pris"),
                                 f_dict.get("storlek")))
        f.write("      %s\n" % string.join(lf, ", "))
        return f.getvalue()

    def to_string_html(self):
        f = cStringIO.StringIO()
        f.write('<TR><TD COLSPAN=2><B>%s (nr <a href=%s>%s</a>) %s</B></TD></TR>\n' % \
                (self.dict["namn"],
                 varu_url(self.dict["varunr"]),
                 self.dict["varunr"],
                 self.typical_price()))

        f.write("<TR><TD>%s<BR>\n" % self.dict["ursprung"])
        f.write("%s</TD>\n" % string.replace(self.dict["alkoholhalt"], "volymprocent", "%"))

        f.write("<TD>%s</TD></TR>\n" % self.clock_table())

        f.write("<TR><TD COLSPAN=2><UL>\n")
        for rubrik in ["f�rg","doft","smak"]:
            if self.dict.has_key(rubrik):
                f.write("<LI>%s" % (self.dict[rubrik]))
        f.write("</UL></TD></TR>\n")
        
        f.write("<TR><TD COLSPAN=2>&nbsp;</TD></TR>\n")


        return f.getvalue()
            

class ProductFromWeb(Product):
    def __init__(self, prodno):
        self.url = varu_url(prodno)
        u = urllib.urlopen(self.url)
        webpage = u.read()
        Product.__init__(self, webpage)


# Search class

search_m = MSet([("typlista",
                  MList("<H2>",
                        MSet([("typrubrik", MSDeH(r'<H2>(.*?) *</H2>')),
                              ("prodlista",
                               MList(r'<tr valign=top><td bgcolor="#[0-9a-fA-F]+" width=320>',
                                     MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                                           ("namn", MS('<B>(.*?)</B>')),
                                           ("�rg�ng", MSDeH(r'<font [^>]*?>(.*?)</font>')),
                                           ("varunr2", MS(r'<font [^>]*?>(.*?)</font>')),
                                           ("land", MS(r'<font [^>]*?>(.*?)</font>')),
                                           ("f�rplista",
                                            MList(r'<font face="Arial, Helvetica, sans-serif" size="2">[0-9]+ml</font>',
                                                  MSet([("volym", MSVolym(r'<font [^>]*?>(.*?)</font>')),
                                                        ("pris", MS(r'<font [^>]*?>(.*?)</font>')),
                                                        ]))),
                                           ]))),
                              ]))),
                 ("antal", MS(r"Din s�kning gav ([0-9]+) tr�ffar.")),
                 ])

class Search:
    def __init__(self, webpage):
        (self.dict, pos) = search_m.match(webpage, 0, len(webpage))

    def valid(self):
        return self.dict.has_key("typlista")
    
    def to_string(self):
        f = cStringIO.StringIO()
        for typ in self.dict["typlista"]:
            f.write(typ["typrubrik"] + "\n\n")
            for vara in typ["prodlista"]:
                f.write("%7s  %s\n" % (vara["varunr"],
                                       vara["namn"]))
                fps = []
                for forp in vara["f�rplista"]:
                    fps.append("%11s (%s)" % (forp["pris"], forp["volym"]))
                #fps_txt = string.join(fps, ", ")
                f.write("         %4s %-32s %s\n" % (vara["�rg�ng"],
                                               vara["land"],
                                               fps[0]))
                for fp in fps[1:]:
                    f.write("                                               %s\n" % fp)
                    
                f.write("\n")
            f.write("\n")
        return f.getvalue()

class SearchFromWeb(Search):
    def __init__(self, key, best = 0, soundex = 0):
        if best:
            ordinarie = "0"
        else:
            ordinarie = "1"
        if soundex:
            soundex = "1"
        else:
            soundex = "0"
        url = "http://www.systembolaget.se/pris/owa/zname?p_namn=%s&p_wwwgrptxt=%%25&p_soundex=%s&p_ordinarie=%s" % (urllib.quote(key), soundex, ordinarie)
        u = urllib.urlopen(url)
        webpage = u.read()
        Search.__init__(self, webpage)



# ProductSearch class

p_search_m = MSet([("rubrik", MSDeH(r'(?s)<H2>(.*?)</H2>')),
                   ("prodlista",
                    MList(r'<A HREF="/pris/owa/xdisplay',
                          MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                                ("namn", MS('<B>(.*?)</B>')),
                                ("�rg�ng", MSDeH(r'<font [^>]*?>(.*?)</font>')),
                                ("varunr2", MS(r'<font [^>]*?>(.*?)</font>')),
                                ("land", MS(r'<font [^>]*?>(.*?)</font>')),
                                ("f�rplista",
                                 MList(r'<font face="Arial, Helvetica, sans-serif" size="2">[0-9]+ml</font>',
                                       MSet([("volym", MSVolym(r'<font [^>]*?>(.*?)</font>')),
                                             ("pris", MS(r'<font [^>]*?>(.*?)</font>')),
                                           ]))),
                                ]))),
                   ("antal", MS(r"Din s�kning gav ([0-9]+) tr�ffar.")),
                   ])

class ProductSearch:
    def __init__(self, webpage):
        (self.dict, pos) = p_search_m.match(webpage, 0, len(webpage))
        
    def valid(self):
        return self.dict.has_key("prodlista")
    
    def to_string(self):
        f = cStringIO.StringIO()
        
        f.write(self.dict["rubrik"] + "\n\n")
        
        for vara in self.dict["prodlista"]:
            f.write("%7s  %s\n" % (vara["varunr"],
                                   vara["namn"]))
            fps = []
            for forp in vara["f�rplista"]:
                fps.append("%11s (%s)" % (forp["pris"], forp["volym"]))
            f.write("         %4s %-32s %s\n" % (vara.get("�rg�ng",""),
                                                 vara["land"],
                                                 fps[0]))
            for fp in fps[1:]:
                f.write("                                               %s\n" % fp)
                    
            f.write("\n")
        f.write("\n")
        return f.getvalue()

class ProductSearchFromWeb(ProductSearch):
    def __init__(self, grupp,
                 typ = None,
                 ursprung = None,
                 min_pris = 0, max_pris = 1000000,
                 best = 0,
                 begr_butik = None,
                 p_type = None,
                 p_prop = None,
                 p_ursprung = None):
        if best:
            ordinarie = "0"
        else:
            ordinarie = "1"

        if begr_butik is None:
            begr_butik = ""

        if p_type is None:
            p_type = "0"

        if p_prop is None:
            p_prop = "0"

        if p_ursprung is None:
            p_ursprung = ""
        else:
            p_ursprung = urllib.quote(string.replace(p_ursprung," ","+"))
        grupp = urllib.quote(grupp)
        url = "http://www.systembolaget.se/pris/owa/xasearch?p_wwwgrp=%s&p_varutyp=&p_ursprung=%s&p_prismin=%s&p_prismax=%s&p_type=%s&p_prop=%s&p_butnr=%s&p_ordinarie=%s&p_rest=0&p_back=" % \
              (grupp, p_ursprung,
               min_pris, max_pris,
               p_type, p_prop,
               begr_butik, ordinarie)

        u = urllib.urlopen(url)
        webpage = u.read()
        ProductSearch.__init__(self, webpage)


# Stores class

stores_butikslista = MList(r'<tr><td width="200" valign=top>',
                           MSet([("kod", MS(r'thebut=([0-9]+)')),
                                 ("ort", MS(r'>(.*?)</a>')),
                                 ("adress", MS(r'<td[^>]*>(.*?)</td>')),
                                 ("telefon", MS(r'<td[^>]*>(.*?)</td>')),
                                 ]))

stores_lan_m = MSet([("namn", MS(r'<H2><B>([^(]*?)\(')),
                     ("varunr", MS(r'\(([0-9]+)\)')),
                     ("l�nslista",
                      MList("<H4>",
                            MSet([("l�n", MS(r'<H4>(.*?)</H4>')),
                                  ("butikslista",
                                   stores_butikslista)
                                  ]))),
                     ])

stores_ejlan_m = MSet([("namn", MS(r'<H2><B>([^(]*?)\(')),
                       ("varunr", MS(r'\(([0-9]+)\)')),
                       ("butikslista", stores_butikslista),
                       ])

class Stores:
    def __init__(self, webpage, single_lan = 0, ort = None):
        self.single_lan = single_lan
        if single_lan:
            matcher = stores_ejlan_m
        else:
            matcher = stores_lan_m
        self.ort = ort
        (self.dict, pos) = matcher.match(webpage, 0, len(webpage))
        
    def valid(self):
        return self.dict.has_key("namn")
    
    def to_string(self, show_heading = 0):
        f = cStringIO.StringIO()
        if show_heading:
            f.write("%s (%s)\n\n" %(self.dict["namn"],
                                    self.dict["varunr"]))
        if self.single_lan:
            f.write(self.to_string_butiklista(self.dict["butikslista"]))
        else:
            for lan in self.dict["l�nslista"]:
                butikslista = self.to_string_butiklista(lan["butikslista"])
                if butikslista:
                    f.write(lan["l�n"] + "\n\n")
                    f.write(butikslista)
                    f.write("\n")

        return f.getvalue()

    def to_string_butiklista(self, butiker):
        f = cStringIO.StringIO()
        for butik in butiker:
            if self.ort and string.find(string.lower(butik["ort"]),
                                        string.lower(self.ort)) <> 0:
                continue
            f.write("  %s, %s (%s) [kod %s]\n" % \
                    (butik["ort"],
                     butik["adress"],
                     butik["telefon"],
                     left_zero_pad(butik["kod"],4)))
        return f.getvalue()

class StoresFromWeb(Stores):
    def __init__(self, prodno, lan, ort):
        url = "http://www.systembolaget.se/pris/owa/zvselect?p_artspec=&p_varunummer=%s&p_lan=%s&p_back=&p_rest=0" % (prodno, lan)
        u = urllib.urlopen(url)
        webpage = u.read()
        Stores.__init__(self, webpage,
                        single_lan = (lan <> "99"),
                        ort = ort)

# HTML-lista

def do_html(nr_lista):
    print "<BODY BGCOLOR=white>"
    print "<TABLE>"
    for varunr in nr_lista:
        prod = ProductFromWeb(varunr)
        if prod.valid():
            print prod.to_string_html()
        else:
            print "<TR><TD COLSPAN=2>Varunr %s saknas.</TD></TR>\n" % varunr
    print "</TABLE>"
    print "<P><FONT SIZE=-2>Uppgifterna �r h�mtade fr�n <A HREF=http://www.systembolaget.se/svenska/varor/prislist/xindex.htm>Systembolagets katalog</A>.</FONT>"
    print "</BODY>"
    

# MAIN

# Option handling

debug = 0
best = 0
soundex = 0
kort = 0
butiker = 0
barabutiker = 0
lan = "99"
ort = None
min_pris = 0
max_pris = 1000000
begr_butik = None
grupp = None
p_type = None
p_prop = None
p_ursprung = None

F_HELP = 0
F_NAMN = 1
F_PRODUKT = 2
F_VARA = 3
F_HTML = 4

funktion = F_HELP

options, arguments = getopt.getopt(sys.argv[1:],
                                   "",
                                   ["debug",
                                    "namn=",
                                    "html=",
                                    "best�llningssortimentet",
                                    "soundex",
                                    "kort",
                                    "butiker",
                                    "bara-butiker",
                                    "l�n=",
                                    "ort=",
                                    "r�da-viner",
                                    "vita-viner",
                                    "�vriga-viner",
                                    "starkvin",
                                    "sprit",
                                    "�l-och-cider",
                                    "blanddrycker",
                                    "l�ttdrycker",
                                    "min-pris=",
                                    "max-pris=",
                                    "begr�nsa-butik=",
                                    "sm�-flaskor",
                                    "stora-flaskor",
                                    "bag-in-box",
                                    "papp-f�rpackning",
                                    "kosher",
                                    "ekologiskt-odlat",
                                    "nyheter",
                                    "ursprung=",
                                    ])

for (opt, optarg) in options:
    if opt == "--debug":
        debug = 1
    elif opt == "--namn":
        funktion = F_NAMN
        namn = optarg
    elif opt == "--html":
        funktion = F_HTML
        nr_lista = optarg
    elif opt == "--best�llningssortimentet":
        best = 1
    elif opt == "--soundex":
        soundex = 1
    elif opt == "--kort":
        kort = 1
    elif opt == "--butiker":
        butiker = 1
    elif opt == "--bara-butiker":
        butiker = 1
        barabutiker = 1
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
    elif opt == "--vita-viner":
        funktion = F_PRODUKT
        grupp = "VITA VINER"
    elif opt == "--�vriga-viner":
        funktion = F_PRODUKT
        grupp = "�VRIGA VINER"
    elif opt == "--starkvin":
        funktion = F_PRODUKT
        grupp = "STARKVIN M. M."
    elif opt == "--sprit":
        funktion = F_PRODUKT
        grupp = "SPRIT"
    elif opt == "--�l-och-cider":
        funktion = F_PRODUKT
        grupp = "�L & CIDER"
    elif opt == "--blanddrycker":
        funktion = F_PRODUKT
        grupp = "BLANDDRYCKER"
    elif opt == "--l�ttdrycker":
        funktion = F_PRODUKT
        grupp = "L�TTDRYCKER"
    elif opt == "--min-pris":
        min_pris = optarg
    elif opt == "--max-pris":
        max_pris = optarg
    elif opt == "--begr�nsa-butik":
        begr_butik = optarg
    elif opt == "--sm�-flaskor":
        p_type="1"
    elif opt == "--stora-flaskor":
        p_type="2"
    elif opt == "--bag-in-box":
        p_type="3"
    elif opt == "--papp-f�rpackning":
        p_type="4"
    elif opt == "--kosher":
        p_prop="3"
    elif opt == "--ekologiskt-odlat":
        p_prop="2"
    elif opt == "--nyheter":
        p_prop="4"
    elif opt == "--ursprung":
        p_ursprung = optarg
    else:
        sys.stderr.write("Internt fel (%s ej behandlad)" % opt)
        sys.exit(1)

if funktion == F_HELP and len(arguments) > 0:
    funktion = F_VARA

if funktion == F_VARA:
    # Varufunktion
    for varunr in arguments:
        prod = ProductFromWeb(varunr)
        if not barabutiker:
            if prod.valid():
                if kort:
                    txt = prod.to_string_brief()
                else:
                    txt = prod.to_string()
                print txt
            else:
                print "Varunummer %s verkar inte finnas." % varunr
                continue
        
        if butiker:
            stores = StoresFromWeb(varunr, lan, ort)
            if stores.valid():
                print stores.to_string(show_heading = barabutiker)
            else:
                print "Inga butiker med vara %s funna." % varunr
            
elif funktion == F_HTML:
    # HTML-lista
    do_html(string.split(nr_lista,","))
           
elif funktion == F_NAMN:
    # Namns�kning
        s = SearchFromWeb(namn, best, soundex)
        if s.valid():
            print s.to_string(),
        else:
            print "S�kningen gav inga svar."

elif funktion == F_PRODUKT:
    # Produkts�kning
        s = ProductSearchFromWeb(grupp,
                                 min_pris = min_pris,
                                 max_pris = max_pris,
                                 best = best,
                                 begr_butik = begr_butik,
                                 p_type = p_type,
                                 p_prop = p_prop,
                                 p_ursprung = p_ursprung)
        if s.valid():
            print s.to_string(),
        else:
            print "S�kningen gav inga svar."

else: # F_HELP
    print "systembolaget.py --- kommandoradss�kning i Systembolagets katalog"
    print "-----------------------------------------------------------------"
    print 
    print "Varuvisning (med m�jlighet att visa butiker som har varan):"
    print """
   %s [--kort] [--butiker] [--bara-butiker]
   %s [--l�n=L�N] [--ort=ORT]
   %s VARUNR...
""" % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*2)
    print "Varuvisning i HTML-format:"
    print """
   %s --html VARUNR,VARUNR,...
""" % ((sys.argv[0],))
    print "Namns�kning:"
    print """
   %s [--best�llningssortimentet] [--soundex]
   %s  --namn=NAMN
""" % (sys.argv[0], " " * len(sys.argv[0]))
    print "Produkts�kning:"
    print """
   %s { --r�da-viner   | --vita-viner   |
   %s   --�vriga-viner | --starkvin     |
   %s   --sprit        | --�l-och-cider |
   %s   --blanddrycker | --l�ttdrycker }
   %s [--min-pris=MIN] [--max-pris=MAX]
   %s [{--sm�-flaskor  | --stora-flaskor |
   %s   --bag-in-box   | --papp-f�rpackning}]
   %s [{--kosher | --ekologiskt-odlat | --nyheter}
   %s [--ursprung=LAND/REGION]
   %s [--begr�nsa-butik=BUTIKSKOD]
""" % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*9)
    
    
