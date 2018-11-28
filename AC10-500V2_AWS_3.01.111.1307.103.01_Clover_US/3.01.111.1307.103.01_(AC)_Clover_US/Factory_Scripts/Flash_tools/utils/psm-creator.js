var wmcrc = require('./lib/wmcrc.js');
var fs = require('fs');
var crypto = require('crypto');
var parseArgs = require('minimist');
var myArgs = parseArgs(process.argv.slice(2), opts={string:'psm_enc_key', string:'psm_nonce'});

if (myArgs.h === true || myArgs.help === true ) {
	console.log("Usage:\r\nnode psm-creator.js --cfg <config file> --out <output file>");
	process.exit(1);
}

if (typeof myArgs.cfg === "undefined" || typeof myArgs.out === "undefined") {
	console.log("Usage:\r\nnode psm-creator.js --cfg <config file> --out <output file>");
	process.exit(1);
}

var fd = fs.openSync(myArgs.out, 'w');
var psm_enc_key = myArgs.psm_enc_key;
var psm_nonce = myArgs.psm_nonce;
var max_file_size = 2048;

var LineByLineReader = require('line-by-line'),
	    lr = new LineByLineReader(myArgs.cfg, {skipEmptyLines: true});
var obj_id = 1;

function hexSeqtoBuf(hexseq) {
	var len = Math.floor((hexseq.length + 1) / 2 );
	var buf = new Buffer(len);
	buf.fill(0);

	for (var i = 0; i < len; i++) {
		var tmp = "0x"+hexseq[2*i]+""+hexseq[2*i+1];
		buf[i] = parseInt(tmp);
	}
	return buf;
}

function generate_psm_data(name, value, binary) {
	var outbuf = new Buffer(12);
	var val_len = value.length;

	var crc = wmcrc.crc32(Buffer(name));
	if (binary) {
		val_len = Math.floor((val_len + 1) / 2);
		value = hexSeqtoBuf(value);
	}
	crc = wmcrc.crc32(Buffer(value), crc);
	
	outbuf.fill(0xff);
	/* Write Type */
	outbuf.writeUInt16LE(0xaa55, 0);

	/* Write Flags */
	outbuf[2] = 0xff;

	/* Write Data Length */
	outbuf.writeUInt16LE(val_len, 7);

	/* Write Object ID */
	outbuf.writeUInt16LE(obj_id, 9);
	obj_id++;

	/* Write Name Length */
	outbuf[11] = name.length;

	/* Calculate and write CRC */
	crc = wmcrc.crc32(outbuf, crc);
	outbuf.writeUInt32LE(crc, 3);

	fs.writeSync(fd, outbuf, 0, outbuf.length, null);
	fs.writeSync(fd, Buffer(name), 0, name.length, null);
	if (binary) {
		fs.writeSync(fd, value, 0, val_len, null);
	} else {
		fs.writeSync(fd, Buffer(value), 0, val_len, null);
	}
}

function encrypt_psm()
{
	var iv = new Buffer(psm_nonce, 'hex');
	var enc_key = new Buffer(psm_enc_key, 'hex');
	var plainText = new Buffer(fs.readFileSync(myArgs.out), 'hex');
	var cipherText = new Buffer(max_file_size, 'hex');

	var cipher = crypto.createCipheriv('aes-128-ctr', enc_key, iv);
	cipherText = cipher.update(plainText, 'hex', 'hex');
	cipherText += cipher.final('hex');

	fs.writeFileSync(myArgs.out, cipherText, 'hex');
}

lr.on('error', function (err) {
	console.log("Error reading configuration file");
	process.exit(1);
});

lr.on('line', function (line) {
	/* Ignore comments */
	if (line.indexOf('#') === 0) {
		return;
	}

	var components = line.split("=:");
	if (components.length == 2) {
		generate_psm_data(components[0], components[1], true);
	} else {
		components = line.split("=");
		if (components.length == 2) {
			generate_psm_data(components[0], components[1], false);
		}
	}
});

lr.on('end', function () {
	fs.closeSync(fd);
	if (typeof psm_enc_key !== "undefined" && typeof psm_nonce !== "undefined")
		encrypt_psm();
	console.log("Done");
});
