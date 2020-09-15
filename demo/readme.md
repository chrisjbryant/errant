## SERRANT Demo

Assuming you have read the main readme and installed SERRANT successfully, you can try running it on the sample text in this directory to make sure it's running properly:

#### Annotated by ERRANT:

`serrant_parallel -orig orig.txt -cor cor.txt -out test_errant.m2 -annotator errant`

This should produce a file called `test_errant.m2` which is identical to `out_errant.m2`.

#### Annotated by SerCl:

`serrant_parallel -orig orig.txt -cor cor.txt -out test_sercl.m2 -annotator sercl`

This should produce a file called `test_sercl.m2` which is identical to `out_sercl.m2`.

#### Our combination of both:

`serrant_parallel -orig orig.txt -cor cor.txt -out test_combined.m2 -annotator combined`

This should produce a file called `test_combined.m2` which is identical to `out_combined.m2`.
