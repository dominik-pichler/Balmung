In order to export the Markdown notes, the following command can be used: 

```
pandoc ER-NLP.md -s -o output.pdf -V geometry:margin=1in -V header-includes="\usepackage{titlesec} \titlespacing*{\section}{0pt}{6em}{1em}"
```


or 


```
pandoc ER-NLP.md -s -o output.pdf -V geometry:margin=1in -V header-includes="\usepackage{titlesec} \titlespacing*{\section}{0pt}{2em}{1em} \titlespacing*{\subsection}{0pt}{1.5em}{0.75em} \titlespacing*{\subsubsection}{0pt}{1em}{0.5em}"

```