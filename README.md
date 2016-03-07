Some code to print stickers on a WASP WPL305 label printer
==========================================================

You'll need hexdump from here:

https://pointless.net/hg/hexdump/file/

To Test
-------

curl -H "Content-Type: application/json" \
-X POST -d '{"owner_id":"42","owner_name":"test"}' \
http://kiosk:12345/print/box

or put your json in test.json and:

curl --verbose -H "Content-Type: application/json"\
 -X POST --data @test.json \
http://kiosk:12345/print/box
