"""
Email templates used by the flaks server to send an error when jobs_done fails.
"""

EMAIL_PLAINTEXT = """
An error happened when processing your push!

{error_traceback}

{pretty_json}
"""

# css theme taken from:
#   https://github.com/dracula/pygments/blob/master/dracula.css
# replaced all '{' and '}' by '{{' and '}}' in the stylesheet because we use str.format to interpolate the contents
EMAIL_HTML = """
<!DOCTYPE html>
<html>

<head>
  <style type="text/css" media="screen">
 .highlight .hll {{ background-color: #f1fa8c }}
 .highlight  {{ background: #282a36; color: #f8f8f2 }}
 .highlight .c {{ color: #6272a4 }}
 .highlight .err {{ color: #f8f8f2 }}
 .highlight .g {{ color: #f8f8f2 }}
 .highlight .k {{ color: #ff79c6 }}
 .highlight .l {{ color: #f8f8f2 }}
 .highlight .n {{ color: #f8f8f2 }}
 .highlight .o {{ color: #ff79c6 }}
 .highlight .x {{ color: #f8f8f2 }}
 .highlight .p {{ color: #f8f8f2 }}
 .highlight .ch {{ color: #6272a4 }}
 .highlight .cm {{ color: #6272a4 }}
 .highlight .cp {{ color: #ff79c6 }}
 .highlight .cpf {{ color: #6272a4 }}
 .highlight .c1 {{ color: #6272a4 }}
 .highlight .cs {{ color: #6272a4 }}
 .highlight .gd {{ color: #8b080b }}
 .highlight .ge {{ color: #f8f8f2; text-decoration: underline }}
 .highlight .gr {{ color: #f8f8f2 }}
 .highlight .gh {{ color: #f8f8f2; font-weight: bold }}
 .highlight .gi {{ color: #f8f8f2; font-weight: bold }}
 .highlight .go {{ color: #44475a }}
 .highlight .gp {{ color: #f8f8f2 }}
 .highlight .gs {{ color: #f8f8f2 }}
 .highlight .gu {{ color: #f8f8f2; font-weight: bold }}
 .highlight .gt {{ color: #f8f8f2 }}
 .highlight .kc {{ color: #ff79c6 }}
 .highlight .kd {{ color: #8be9fd; font-style: italic }}
 .highlight .kn {{ color: #ff79c6 }}
 .highlight .kp {{ color: #ff79c6 }}
 .highlight .kr {{ color: #ff79c6 }}
 .highlight .kt {{ color: #8be9fd }}
 .highlight .ld {{ color: #f8f8f2 }}
 .highlight .m {{ color: #bd93f9 }}
 .highlight .s {{ color: #f1fa8c }}
 .highlight .na {{ color: #50fa7b }}
 .highlight .nb {{ color: #8be9fd; font-style: italic }}
 .highlight .nc {{ color: #50fa7b }}
 .highlight .no {{ color: #f8f8f2 }}
 .highlight .nd {{ color: #f8f8f2 }}
 .highlight .ni {{ color: #f8f8f2 }}
 .highlight .ne {{ color: #f8f8f2 }}
 .highlight .nf {{ color: #50fa7b }}
 .highlight .nl {{ color: #8be9fd; font-style: italic }}
 .highlight .nn {{ color: #f8f8f2 }}
 .highlight .nx {{ color: #f8f8f2 }}
 .highlight .py {{ color: #f8f8f2 }}
 .highlight .nt {{ color: #ff79c6 }}
 .highlight .nv {{ color: #8be9fd; font-style: italic }}
 .highlight .ow {{ color: #ff79c6 }}
 .highlight .w {{ color: #f8f8f2 }}
 .highlight .mb {{ color: #bd93f9 }}
 .highlight .mf {{ color: #bd93f9 }}
 .highlight .mh {{ color: #bd93f9 }}
 .highlight .mi {{ color: #bd93f9 }}
 .highlight .mo {{ color: #bd93f9 }}
 .highlight .sa {{ color: #f1fa8c }}
 .highlight .sb {{ color: #f1fa8c }}
 .highlight .sc {{ color: #f1fa8c }}
 .highlight .dl {{ color: #f1fa8c }}
 .highlight .sd {{ color: #f1fa8c }}
 .highlight .s2 {{ color: #f1fa8c }}
 .highlight .se {{ color: #f1fa8c }}
 .highlight .sh {{ color: #f1fa8c }}
 .highlight .si {{ color: #f1fa8c }}
 .highlight .sx {{ color: #f1fa8c }}
 .highlight .sr {{ color: #f1fa8c }}
 .highlight .s1 {{ color: #f1fa8c }}
 .highlight .ss {{ color: #f1fa8c }}
 .highlight .bp {{ color: #f8f8f2; font-style: italic }}
 .highlight .fm {{ color: #50fa7b }}
 .highlight .vc {{ color: #8be9fd; font-style: italic }}
 .highlight .vg {{ color: #8be9fd; font-style: italic }}
 .highlight .vi {{ color: #8be9fd; font-style: italic }}
 .highlight .vm {{ color: #8be9fd; font-style: italic }}
 .highlight .il {{ color: #bd93f9 }}
  </style>
</head>

<body>

<h2>Oops</h2>

<p>An error happened when processing your push!</p>
<p>Usually the problem is your <code>.jobs_done.yaml</code> file. Check the traceback below for clues.</p>

<h2>Traceback</h2>

{error_traceback_html}

<h2>Request</h2>

{pretty_json_html}

</body>
</html>
"""
