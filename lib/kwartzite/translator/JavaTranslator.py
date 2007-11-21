###
### $Rev$
### $Release$
### $Copyright$
###


import os, re
import kwartzite.config as config
from kwartzite.util import qquote, define_properties
from kwartzite.parser.TextParser import ElementInfo, Expression
from kwartzite.translator import Translator



def q(string):
    s = qquote(string)
    L = []
    for line in s.splitlines(True):
        if line.endswith("\r\n"):  line = line[0:-2] + "\\r\\n"
        elif line.endswith("\n"):  line = line[0:-1] + "\\n"
        L.append(line)
    return '"\n             + "'.join(L)



def c(name):
    #return ''.join([ s.capitalize() for s in name.split('_') ])
    return name.title().replace('_', '')



class JavaTranslator(Translator):


    _property_descriptions = (
        ('classname' , 'str'  , 'classname pattern'),
        ('baseclass' , 'str'  , 'parent class name'),
        ('interface' , 'str'  , 'interface name to implements'),
        ('package'   , 'str'  , 'package name'),
        ('encoding'  , 'str'  , 'encoding name'),
        ('mainprog'  , 'bool' , 'define main program or not'),
        ('context'   , 'bool' , 'use context object in constructor or not'),
        ('nullobj'   , 'bool' , 'use NULL object instead of None'),
        ('fragment'  , 'bool' , 'define createElementXxx() and createContentXxx()'),
        ('accessors' , 'bool' , 'define setter and getter or not'),
        ('java5'     , 'bool' , 'use StringBuilder and Map<String,String> if true'),
    )
    define_properties(_property_descriptions, baseclass='Object', context=False)
    if locals()['baseclass'] == 'object': locals()['baseclass'] = 'Object'


    def __init__(self, classname=None, baseclass=None, interface=None, package=None, encoding=None, mainprog=None, context=None, nullobj=None, fragment=None, accessors=None, java5=None, **properties):
        if classname is not None:  self.classname = classname
        if baseclass is not None:  self.baseclass = baseclass
        if interface is not None:  self.interface = interface
        if package   is not None:  self.package   = package
        if encoding  is not None:  self.encoding  = encoding
        if mainprog  is not None:  self.mainprog  = mainprog
        if context   is not None:  self.context   = context
        if nullobj   is not None:  self.nullobj   = nullobj
        if fragment  is not None:  self.fragment  = fragment
        if accessors is not None:  self.accessors = accessors
        if java5     is not None:  self.java5      = java5
        self.nullvalue = nullobj and 'NULL' or 'null'


    def translate(self, template_info, **properties):
        stmt_list  = template_info.stmt_list
        elem_table = template_info.elem_table
        filename   = properties.get('filename') or template_info.filename
        classname  = properties.get('classname') or self.classname
        classname = self.build_classname(filename, pattern=classname, **properties)
        bufclass = self.java5 and 'StringBuilder' or 'StringBuffer'
        buf = []
        extend = buf.extend
        if filename:
            extend((
            '// generated from ', filename, '\n'
            '\n'
            ))
        if self.package:
            extend((
            'package ', self.package, ';\n'
            '\n'
            ))
        s = self.interface and ' implements ' + self.interface or ''
        extend((
            'import java.util.Map;\n'
            'import java.util.HashMap;\n',
            not self.java5 and 'import java.util.Iterator;\n' or '',
            #'static import kwartzite.util.TemplateUtility.*;\n'
            '\n'
            '\n'
            'public class ', classname, ' extends ', self.baseclass, s, ' {\n'
            '\n'
            '    protected ', bufclass, ' _buf;\n'
            '    protected int _bufsize = 1024;\n'
            ,))
        if self.context:
            subtype = self.java5 and '<String,Object>' or ''
            extend((
            '    protected Map', subtype, ' _context;\n'
            '\n'
            '    public ', classname, '() {\n'
            '         this(new HashMap', subtype, '());\n'
            '    }\n'
            '\n'
            '    public ', classname, '(Map', subtype, ' _context) {\n'
            '        this._context = _context;\n'
            ,))
        else:
            extend((
            '\n'
            '    public ', classname, '() {\n'
            ,))
        for name, elem in elem_table.iteritems():
            extend(('        init', c(name), '();\n', ))
        extend((
            '    }\n'
            '\n'
            ,))
        #
        self.expand_utils(buf)
        #
        extend((
            '\n'
            '    public String createDocument() {\n'
            ,))
        #self.expand_stmt_list(buf, stmt_list)
        extend((
            '        appendDocument(new ', bufclass, '(_bufsize));\n'
            '        return _buf.toString();\n'
            '    }\n'
            '\n'
            ,))
        #
        extend((
            '    public void appendDocument(', bufclass, ' buf) {\n'
            '        _buf = buf;\n'
            '        initDocument();\n'
            ,))
        self.expand_stmt_list(buf, stmt_list)
        extend((
            '    }\n'
            '\n'
            '    public void initDocument() {\n'
            '    }\n'
            '\n'
            ,))
        #
        for name, elem in elem_table.iteritems():
            extend((
            '\n'
            '    //\n'
            '    // element \'', name, '\'\n'
            '    //\n'
            '\n'
            ,))
            self.expand_init(buf, elem); buf.append("\n")
            if elem.directive.name != 'mark':  continue
            self.expand_elem(buf, elem); buf.append("\n")
            self.expand_stag(buf, elem); buf.append("\n")
            self.expand_cont(buf, elem); buf.append("\n")
            self.expand_etag(buf, elem); buf.append("\n")
            if self.fragment:
                self.expand_create_element(buf, elem); buf.append("\n")
                self.expand_create_content(buf, elem); buf.append("\n")
        if self.mainprog:
            extend((
            '\n'
            '    // for test\n'
            '    public static void main(String[] args) throws Exception {\n'
            '        System.out.print(new ', classname, '().createDocument());\n'
            '    }\n'
            ,))
        buf.append(
            '\n'
            '}\n'
            ,)
        return ''.join(buf)


    def expand_utils(self, buf):
        subtype = self.java5 and '<String,String>' or ''
        bufclass = self.java5 and 'StringBuilder' or 'StringBuffer'
        if self.nullobj:
            buf.extend((
            '\n'
            '    //public static final Object ', self.nullvalue, ' = new Object();\n'
            '    public static final String ', self.nullvalue, ' = new String("");\n'
            ,))
        buf.extend((
            '\n'
            '    public String toStr(Object value) {\n'
            '        return value == null ? "" : value.toString();\n'
            '    }\n'
            '\n'
            '    public String toStr(String value) {\n'
            '        return value == null ? "" : value;\n'
            '    }\n'
            '\n'
            #'    public String escapeXml(String value) {\n'
            #'        if (value == null) return "";\n'
            #'        return value.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\\"","&quot;");\n'
            #'        \n'
            #'    }\n'
            #'\n'
            #'    public String escapeXml(String str) {\n'
            #'        if (str == null) return "";\n'
            #'        int len = str.length();\n'
            #'        ', bufclass, ' buf = new ', bufclass, '();\n'
            #'        for (int i = 0; i < len; i++) {\n'
            #'            char ch = str.charAt(i);\n'
            #'            if      (ch == \'&\') buf.append("&amp;");\n'
            #'            else if (ch == \'<\') buf.append("&lt;");\n'
            #'            else if (ch == \'>\') buf.append("&gt;");\n'
            #'            else if (ch == \'"\') buf.append("&quot;");\n'
            #'            else                buf.append(ch);\n'
            #'        }\n'
            #'        return buf.toString();\n'
            #'    }\n'
            #'\n'
            #'    public String escapeXml(String value) {\n'
            #'        if (value == null) return "";\n'
            #'        ', bufclass, ' buf = null;\n'
            #'        String s = null;\n'
            #'        for (int i = 0, n = value.length(); i < n; i++) {\n'
            #'            char ch = value.charAt(i);\n'
            #'            switch (ch) {\n'
            #'            case \'&\':  s = "&amp;";  break;\n'
            #'            case \'<\':  s = "&lt;";   break;\n'
            #'            case \'>\':  s = "&gt;";   break;\n'
            #'            case \'"\':  s = "&quot;"; break;\n'
            #'            }\n'
            #'            if (s != null) {\n'
            #'                if (buf == null) {\n'
            #'                    (buf = new ', bufclass, '()).append(value.substring(0, i));\n'
            #'                }\n'
            #'                buf.append(s);\n'
            #'                s = null;\n'
            #'            } else {\n'
            #'                if (buf != null) buf.append(ch);\n'
            #'            }\n'
            #'        }\n'
            #'        return buf == null ? value : buf.toString();\n'
            #'    }\n'
            #'\n'
            #'    public String escapeXml(String str) {\n'
            #'        if (str == null) return "";\n'
            #'        int len = str.length();\n'
            #'        ', bufclass, ' buf = null;\n'
            #'        for (int i = 0; i < len; i++) {\n'
            #'            char ch = str.charAt(i);\n'
            #'            if (ch == \'&\')\n'
            #'                (buf == null ? (buf = new ', bufclass, '()).append(str.substring(0, i)) : buf).append("&amp;");\n'
            #'            else if (ch == \'<\')\n'
            #'                (buf == null ? (buf = new ', bufclass, '()).append(str.substring(0, i)) : buf).append("&lt;");\n'
            #'            else if (ch == \'>\')\n'
            #'                (buf == null ? (buf = new ', bufclass, '()).append(str.substring(0, i)) : buf).append("&gt;");\n'
            #'            else if (ch == \'"\')\n'
            #'                (buf == null ? (buf = new ', bufclass, '()).append(str.substring(0, i)) : buf).append("&quot;");\n'
            #'            else\n'
            #'                if (buf != null) buf.append(ch);\n'
            #'        }\n'
            #'        return buf == null ? str : buf.toString();\n'
            #'    }\n'
            #'\n'
            '    public String escapeXml(String str) {\n'
            '        if (str == null) return "";\n'
            '        int len = str.length();\n'
            '        ', bufclass, ' buf = null;\n'
            '        char ch;\n'
            '        int i;\n'
            '        for (i = 0; i < len; i++) {\n'
            '            ch = str.charAt(i);\n'
            '            if (ch == \'&\') {\n'
            '                (buf = new ', bufclass, '()).append(str.substring(0, i)).append("&amp;");\n'
            '                break;\n'
            '            }\n'
            '            else if (ch == \'<\') {\n'
            '                (buf = new ', bufclass, '()).append(str.substring(0, i)).append("&lt;");\n'
            '                break;\n'
            '            }\n'
            '            else if (ch == \'>\') {\n'
            '                (buf = new ', bufclass, '()).append(str.substring(0, i)).append("&gt;");\n'
            '                break;\n'
            '            }\n'
            '            else if (ch == \'"\') {\n'
            '                (buf = new ', bufclass, '()).append(str.substring(0, i)).append("&quot;");\n'
            '                break;\n'
            '            }\n'
            '        }\n'
            '        if (i == len)\n'
            '            return str;\n'
            '        for (i++ ; i < len; i++) {\n'
            '            ch = str.charAt(i);\n'
            '            if      (ch == \'&\') buf.append("&amp;");\n'
            '            else if (ch == \'<\') buf.append("&lt;");\n'
            '            else if (ch == \'>\') buf.append("&gt;");\n'
            '            else if (ch == \'"\') buf.append("quot;");\n'
            '            else                buf.append(ch);\n'
            '        }\n'
            '        return buf.toString();\n'
            '    }\n'
            '\n'
            '    public void echo(String value) {\n'
            '        _buf.append(value);\n'
            '    }\n'
            '\n'
            '    public void echo(Object value) {\n'
            '        _buf.append(value.toString());\n'
            '    }\n'
            '\n'
            '    public void appendAttribute(Map', subtype, ' attr) {\n'
            ,))
        if self.java5:
            buf.extend((
            '        for (Map.Entry<String,String> entry: attr.entrySet()) {\n'
            '            String key = entry.getKey();\n'
            '            String val = entry.getValue();\n'
            ,))
        else:
            buf.extend((
            '        for (Iterator it = attr.entrySet().iterator(); it.hasNext(); ) {\n'
            '            Map.Entry entry = (Map.Entry)it.next();\n'
            '            Object key = entry.getKey();\n'
            '            Object val = entry.getValue();\n'
            ,))
        buf.extend((
            '            if (val != ', self.nullvalue, ') {\n'
            '                _buf.append(\' \').append(key).append("=\\"").append(toStr(val)).append(\'"\');\n'
            #'                _buf.append(\' \').append(key).append("=\\"").append(val).append(\'"\');\n'
            '            }\n'
            '        }\n'
            '    }\n'
            ,))


    def expand_stmt_list(self, buf, stmt_list):
        def flush(L, buf):
            if L:
                buf.append('        _buf')
                for s in L:
                    buf.extend(('.append(', s, ')', ))
                buf.append(';\n')
                L[:] = ()
        L = []
        for item in stmt_list:
            if isinstance(item, (str, unicode)):
                #s = item.endswith('\n') and '\n            ' or ''
                s = ''
                L.append('"' + q(item) + '"' + s)
            elif isinstance(item, ElementInfo):
                flush(L, buf)
                elem = item
                assert elem.directive.name == 'mark'
                buf.extend(("        elem", c(elem.name), "();\n", ))
            elif isinstance(item, Expression):
                expr = item
                kind = expr.kind
                if   kind == 'text':
                    L.append("toStr(text" + c(expr.name) + ")")
                elif kind == 'attr':
                    flush(L, buf)
                    buf.extend(("        appendAttribute(attr", c(expr.name), ");\n", ))
                elif kind == 'node':
                    L.append("toStr(self.node" + c(expr.name) + ")")
                elif kind == 'native':
                    L.append("toStr(" + expr.code + ")")
                else:
                    assert "** unreachable"
            else:
                assert "** unreachable"
        flush(L, buf)


    def expand_init(self, buf, elem):
        name = elem.name
        extend = buf.extend
        ## instance variable declaration
        initval = not elem.cont_text_p() and (' = '+self.nullvalue) or ''
        d_name = elem.directive.name
        subtype = self.java5 and '<String,String>' or ''
        if d_name in ('mark', 'attr', 'textattr'):
            if not self.accessors:
                extend((
                    '    public Map', subtype, ' attr', c(name), ';\n'
                    ,))
            else:
                extend((
                    '    protected Map', subtype, ' attr', c(name), ';\n'
                    '    public String attr', c(name), '(String name) {\n'
                    '        return (String)attr', c(name), '.get(name);\n'
                    '    }\n'
                    '    public void put', c(name), '(String name, String value, boolean escape) {\n'
                    '        attr', c(name), '.put(name, value == null ? null : (escape ? escapeXml(value) : value));\n'
                    '    }\n'
                    '    public void put', c(name), '(String name, String value) {\n'
                    '        put', c(name), '(name, value, true);\n'
                    #'        attr', c(name), '.put(name, value == null ? null : escapeXml(value));\n'
                    '    }\n'
                    '\n'
                    ,))
        if d_name in ('mark', 'text', 'textattr'):
            if not self.accessors:
                extend((
                    '    public String text', c(name), initval, ';\n'
                    ,))
            else:
                extend((
                    '    protected String text', c(name), initval, ';\n'
                    '    public String get', c(name), '() {\n'
                    '        return text', c(name), ';\n'
                    '    }\n'
                    '    public void set', c(name), '(String value, boolean escape) {\n'
                    '        text', c(name), ' = value == null ? null : (escape ? escapeXml(value) : value);\n'
                    '    }\n'
                    '    public void set', c(name), '(String value) {\n'
                    '        set', c(name), '(value, true);\n'
                    #'        text', c(name), ' = value == null ? null : escapeXml(value);\n'
                    '    }\n'
                    ,))
                if elem.cont_text_p():
                    assert len(elem.cont) == 1
                    if re.match(r'^[-+]?\d+$', elem.cont[0]):
                        extend((
                    '    public void set', c(name), '(int value) {\n'
                    '        text', c(name), ' = String.valueOf(value);\n'
                    '    }\n'
                    ,))
                    elif re.match(r'^[-+]?\d+\.\d+$', elem.cont[0]):
                        extend((
                    '    public void set', c(name), '(double value) {\n'
                    '        text', c(name), ' = String.valueOf(value);\n'
                    '    }\n'
                    ,))
                extend((
                    '\n'
                    ,))
        if d_name in ('mark', 'node'):
            if not self.accessors:
                extend((
                    '    public String node', c(name), ' = ', self.nullvalue, ';\n'
                    ,))
            else:
                extend((
                    '    protected String node', c(name), ' = ', self.nullvalue, ';\n'
                    #'    public String getNode', c(name), '() {\n'
                    #'        return node', c(name), ';\n'
                    #'    }\n'
                    '    public void setNode', c(name), '(String value, boolean escape) {\n'
                    '        node', c(name), ' = value == null ? null : (escape ? escapeXml(value) : value);\n'
                    '    }\n'
                    '    public void setNode', c(name), '(String value) {\n'
                    '        setNode', c(name), '(value, true);\n'
                    '    }\n'
                    '\n'
                    ,))

        ## start of init_xxx
        extend((
            '\n'
            '    public void init', c(name), '() {\n'
            ))
        ## attr_xxx
        if d_name in ('mark', 'attr', 'textattr'):
            extend((
            '        attr', c(name), ' = new HashMap', subtype, '();\n'
            ))
            for space, aname, avalue in elem.attr:
                if isinstance(avalue, Expression):
                    s = avalue.code;
                else:
                    s = '"' + q(avalue) + '"'
                extend((
            '        attr', c(name), '.put("', aname, '", ', s, ');\n',
            ))
        ## text_xxx
        if d_name in ('mark', 'text', 'textattr'):
            if elem.cont_text_p():
                assert len(elem.cont) == 1
                extend((
            '        text', c(name), ' = "', q(elem.cont[0]), '";\n'
            ))
        ## end of init_xxx
        extend((
            '    }\n',
            ))


    def expand_elem(self, buf, elem):
        name = elem.name
        buf.extend((
            '    public void elem', c(name), '() {\n'
            '        if (node', c(name), ' == ', self.nullvalue, ') {\n'
            '            stag', c(name), '();\n'
            '            cont', c(name), '();\n'
            '            etag', c(name), '();\n'
            '        } else {\n'
            '            _buf.append(toStr(node', c(name), '));\n'
            '        }\n'
            '    }\n'
            ))


    def expand_stag(self, buf, elem):
        name = elem.name
        extend = buf.extend
        stag = elem.stag
        extend((
            '    public void stag', c(name), '() {\n'
            ))
        if stag.name:
            extend((
            '        _buf.append("', stag.head_space or '', '<', stag.name, '");\n'
            '        appendAttribute(attr', c(name), ');\n'
            '        _buf.append("', q(stag.extra_space or ''), stag.is_empty and ' />' or '>', q(stag.tail_space or ''), '");\n',
            ))
        else:
            s = (stag.head_space or '') + (stag.tail_space or '')
            if s:
                extend(('        _buf.append("', q(s), '");\n', ))
        buf.append(
            '    }\n'
            )


    def expand_cont(self, buf, elem):
        name = elem.name
        extend = buf.extend
        extend((
            '    public void cont', c(name), '() {\n',
            ))
        if elem.cont_text_p():
            extend((
            '        if (text', c(name), ' != ', self.nullvalue, ')\n'
            '            _buf.append(text', c(name), ');\n'
            ))
        else:
            extend((
            '        if (text', c(name), ' != ', self.nullvalue, ') {\n'
            '            _buf.append(text', c(name), ');\n'
            '            return;\n'
            '        }\n',
            ))
            if elem.cont:
                self.expand_stmt_list(buf, elem.cont)
        buf.append(
            '    }\n'
            )


    def expand_etag(self, buf, elem):
        name = elem.name
        extend = buf.extend
        etag = elem.etag
        extend((
            '    public void etag', c(name), '() {\n',
            ))
        if not etag:
            extend((
            '        //\n'
            ))
        elif etag.name:
            s1 = q(etag.head_space or '')
            s2 = q(etag.tail_space or '')
            extend((
            '        _buf.append("', s1, '</', etag.name, '>', s2, '");\n',
            ))
        else:
            s = (etag.head_space or '') + (etag.tail_space or '')
            if s:
                extend(('        _buf.append("', q(s), '");\n', ))
            else:
                buf.append('        //\n')
        buf.append(
            '    }\n'
            )


    def _expand_create_element_or_content(self, buf, elem, kind):
        s1, s2 = kind == 'element' and ('Element', 'elem') or ('Content', 'cont')
        bufclass = self.java5 and 'StringBuilder' or 'StringBuffer'
        name = elem.name
        extend = buf.extend
        extend((
            '    public void append', s1, c(name), '(', bufclass, ' _buf) {\n'
            '        this._buf = _buf;\n'
            '        ', s2, c(name), '();\n'
            '    }\n'
            #'\n'
            '    public String create', s1, c(name), '() {\n'
            '        this._buf = new ', bufclass, '();\n'
            '        ', s2, c(name), '();\n'
            '        return _buf.toString();\n'
            '    }\n'
            ,))


    def expand_create_element(self, buf, elem):
        self._expand_create_element_or_content(buf, elem, 'element')


    def expand_create_content(self, buf, elem):
        self._expand_create_element_or_content(buf, elem, 'content')
