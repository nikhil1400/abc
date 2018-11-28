var parseArgs = require('minimist');
var myArgs = parseArgs(process.argv.slice(2), opts={string:'fw_enc_key', string:'fw_nonce'});

var Buffer = require('buffer').Buffer;
var fs = require('fs');
var constants = require('constants');
var crypto = require('crypto');
var sjcl = require('./lib/sjcl.js');
var NodeRSA = require('node-rsa');
var wmcrc = require('./lib/wmcrc.js');
var forsake = require('forsake');
var path = require('path');

if (myArgs.h === true || myArgs.help === true ) {
	Usage();
}

if (typeof myArgs.inf === "undefined") {
	Usage();
}

function Usage() {
	console.log("Usage:\r\nnode gen_app_fw.js --inf <input file> [--fw_enc_algo <encryption algorithm> --fw_enc_key <128-bit encryption key>"
			+ " --fw_nonce <128-bit nonce> --fw_sign_algo <signing algorithm> --fw_hash_algo <hashing algorithm>"
			+ " --fw_pub_key <PEM public key file> --fw_prv_key <PEM private key file>"
			+ " --outf <output file name>]");
	process.exit(0);
}

var ip_file = myArgs.inf;
var op_file = myArgs.outf;
var fw_enc_algo = myArgs.fw_enc_algo;
var fw_enc_key = myArgs.fw_enc_key;
var fw_sign_algo = myArgs.fw_sign_algo;
var fw_hash_algo = myArgs.fw_hash_algo;
var fw_pub_key = myArgs.fw_pub_key;
var fw_prv_key = myArgs.fw_prv_key;
var fw_nonce = myArgs.fw_nonce;

/* tlv header elements */
var tlv_hdr_magic = new Uint32Array(1);
var tlv_hdr_len = new Uint32Array(1);
var tlv_hdr_crc = new Uint32Array(1);

/* tlv buffer parameters */
var tlv_buf_offset = 0;
var tlv_buf = new Buffer(100000);
tlv_buf.fill(0);

var tlv_fw_len_type = 40;
var tlv_fw_nonce_type = 39;
var tlv_fw_sig_type = 65;
var tlv_key_filler_type = 255;

var is_xip = false;

var app_fw_buf = new Buffer(fs.readFileSync(ip_file), 'hex');

/* Validate application firmware */
var magic_str = app_fw_buf.slice(0, 4);
if (magic_str != 'LVRM' && magic_str != 'MRVL') {
	console.error("Invalid application firmware. Exiting.");
	process.exit(1);
}

var magic_sig = app_fw_buf.readUInt32LE(4);
if (magic_sig != 0x2e9cf17b && magic_sig != 0x7bf19c2e) {
	console.error("Invalid application firmware. Exiting.");
	process.exit(1);
}

/* Check if XIP is enabled and encryption is required */
var entry = app_fw_buf.readUInt32LE(16);
if (((entry & 0x1f000000) === 0x1f000000) || (entry & 0x0000001f) === 0x0000001f)
	is_xip = true;


if (typeof fw_enc_algo === "undefined" && typeof fw_sign_algo === "undefined") {
	console.error("Info: No encryption or signing was asked for firmware");
	console.error("Info: Doing nothing for firmware image");
	var filename = get_outfile_name();
	fs.writeFileSync(filename, app_fw_buf, 'hex');
	process.exit(0);
}

if (typeof fw_enc_algo !== "undefined") {
	if (is_xip == true) {
		console.error("Encryption of XIP firmware is not allowed");
		process.exit(1);
	}

	if (fw_enc_algo !== "AES_CTR_128_ENCRYPT") {
		console.error("Firmware Encryption algorithm " + fw_enc_algo + " is not supported");
		process.exit(1);
	}
	if (typeof fw_enc_key === "undefined") {
		console.error("Encryption key is not specified");
		process.exit(1);
	}

	var enc_key = new Buffer(fw_enc_key, 'hex');

	if (typeof fw_nonce === "undefined") {
		/* Generate 16-digit random IV */
		iv = crypto.randomBytes(16).toString('hex');
	} else {
		iv = fw_nonce;
	}

	iv = new Buffer(iv, 'hex');

	var cipherText = new Buffer(app_fw_buf.length);

	var cipher = crypto.createCipheriv('aes-128-ctr', enc_key, iv);
	cipherText = cipher.update(app_fw_buf, 'hex', 'hex');
	cipherText += cipher.final('hex');

	app_fw_buf.write(cipherText, 0, cipherText.length, 'hex');

	if (typeof fw_sign_algo === "undefined") {
		generate_keystore();
	}
}

if (typeof fw_sign_algo !== "undefined") {
	if (fw_sign_algo !== "RSA_SIGN") {
		console.error("Firmware Signing method " + fw_sign_algo + " is not supported");
		process.exit(1);
	}
	if (typeof fw_hash_algo === "undefined") {
		console.error("Firmware Hash algorithm is not specified");
		process.exit(1);
	}
	if (fw_hash_algo !== "SHA256_HASH") {
		console.error("Firmware Hash algorithm " + fw_hash_algo + " is not supported");
		process.exit(1);
	}
	/* Find hash of boot2 */
	var shasum = crypto.createHash('sha256');

	shasum.update(app_fw_buf);
	var app_fw_hash = shasum.digest('hex');
	console.log("MCUFW HASH " + app_fw_hash);

	if (typeof fw_pub_key === "undefined") {
		console.error("Firmware public key for signing is not specified");
		process.exit(1);
	}
	if (typeof fw_prv_key === "undefined") {
		console.error("Firmware private key for signing is not specified");
		process.exit(1);
	}
	prvKey = fs.readFileSync(fw_prv_key);
	pubKey = fs.readFileSync(fw_pub_key);

	var digital_sig;

	app_fw_hash = new Buffer(app_fw_hash, 'hex');
	var sign = forsake.sign(app_fw_hash, prvKey);
	var tmp_buf = new Buffer(sign, 'base64');
	digital_sig = tmp_buf.toString('hex');
	console.log("MCUFW SIGNATURE " + digital_sig);
	generate_keystore();
}

/* Initialize TLV header */
function tlv_init() {
	tlv_hdr_len = tlv_hdr_magic.BYTES_PER_ELEMENT +
		tlv_hdr_len.BYTES_PER_ELEMENT +
		tlv_hdr_crc.BYTES_PER_ELEMENT;
	tlv_hdr_magic = 0x53424648;
	/* CRC is initialized to max tlv size(4K) */
	tlv_hdr_crc = 0x00001000;

	/* Write initial values to tlv buffer */
	tlv_buf.writeUInt32BE(tlv_hdr_magic, tlv_buf_offset, 4, 'hex');
	tlv_buf_offset += 4;
	tlv_buf.writeUInt32LE(tlv_hdr_len, tlv_buf_offset, 4, 'hex');
	tlv_buf_offset += 4;
	tlv_buf.writeUInt32LE(tlv_hdr_crc, tlv_buf_offset, 4, 'hex');
	tlv_buf_offset += 4;
}

function add_tlv_data(type, length, value, encoding) {
	tlv_buf.writeUInt32LE(type, tlv_buf_offset, 1, 'hex');
	tlv_buf_offset += 1;
	tlv_buf.writeUInt32LE(length, tlv_buf_offset, 2, 'hex');
	tlv_buf_offset += 2;
	if (typeof encoding === "undefined")
		tlv_buf.write(value, tlv_buf_offset, length, 'hex');
	else if (encoding === 'hex')
		tlv_buf.writeUInt32LE(value, tlv_buf_offset, length, 'hex');
	else
		tlv_buf.write(value, tlv_buf_offset, length, encoding);
	tlv_buf_offset += length;
}

function tlv_close() {
	var tlv_hdr_len_offset = 4;
	var tlv_hdr_crc_offset = 8;

	tlv_crc_buf = tlv_buf.slice(tlv_hdr_len, tlv_buf_offset);

	tlv_buf.writeUInt32LE(tlv_buf_offset, tlv_hdr_len_offset, 4, 'hex');
	tlv_buf.writeUInt32LE(wmcrc.crc32(tlv_crc_buf), tlv_hdr_crc_offset, 4, 'hex');
	tlv_buf = tlv_buf.slice(0, tlv_buf_offset);
}

function get_outfile_name() {
	if (typeof op_file !== "undefined")
		return op_file;

	var filename = path.basename(ip_file, '.bin');
	
	if (typeof fw_enc_algo !== "undefined" || typeof fw_sign_algo !== "undefined")
		filename = filename + ".";

	if (typeof fw_enc_algo !== "undefined")
		filename = filename + "e";
	if (typeof fw_sign_algo !== "undefined")
		filename = filename + "s";

	filename = filename + ".bin";

	return filename;
}

function write_app_fw() {
	var filename = get_outfile_name();
	fs.writeFileSync(filename, tlv_buf, 'hex');
	fs.appendFileSync(filename, app_fw_buf, 'hex');
	console.log("\r\nGenerated " + filename);
}

function generate_keystore() {
	tlv_init();
	if (typeof fw_enc_algo !== "undefined" || typeof fw_sign_algo !== "undefined") {
		/* Add firmware length to the tlv */
		add_tlv_data(tlv_fw_len_type, 4, app_fw_buf.length, 'hex');
	}
	if (typeof fw_enc_algo !== "undefined") {
		add_tlv_data(tlv_fw_nonce_type, iv.length, iv.toString('hex'));
	}
	if (typeof fw_sign_algo !== "undefined") {
		add_tlv_data(tlv_fw_sig_type, 256, digital_sig);
		if (is_xip === true) {
			var xip_align_size = 4;
			if (tlv_buf_offset & (xip_align_size - 1)) {
				var len = xip_align_size - ((tlv_buf_offset + 1
						+ 2 + xip_align_size)
						& (xip_align_size - 1));

				if ((tlv_buf_offset + len) > tlv_hdr_crc)
					process.exit(1);
				
				var pad_buf = new Buffer(len);
				pad_buf.fill(0xFF);
				add_tlv_data(tlv_key_filler_type, len, pad_buf.toString('hex'));
			}
		}
	}
	tlv_close();
	write_app_fw();
}

