var parseArgs = require('minimist');
var myArgs = parseArgs(process.argv.slice(2), opts={string:'fw_enc_key', string:'boot2_nonce', string:'boot2_enc_key'});

var Buffer = require('buffer').Buffer;
var fs = require('fs');
var constants = require('constants');
var crypto = require('crypto');
var sjcl = require('./lib/sjcl.js');
var NodeRSA = require('node-rsa');
var wmcrc = require('./lib/wmcrc.js');
var forsake = require('forsake');

if (myArgs.h === true || myArgs.help === true ) {
	Usage();
}

if (typeof myArgs.inf === "undefined") {
	Usage();
}

function Usage() {
	console.log("Usage:\r\nnode gen_boot2.js --inf <input file> [--fw_enc_algo <mcufw encryption algorithm> --fw_enc_key <128-bit encryption key>"
			 + " --fw_sign_algo <mcufw signing algorithm> --fw_hash_algo <mcufw hashing algorithm> --fw_pub_key <mcufw PEM public key file>"
			 + " --boot2_enc_algo <boot2 encryption algorithm>] --boot2_enc_key <256-bit encryption key> --boot2_nonce <12-byte nonce>"
			 + " --boot2_sign_algo <boot2 signing algorithm> --boot2_prv_key <Boot2 PEM private key file> --boot2_pub_key <Boot2 PEM public key file>"
			 + " --ks <type:value type:value>"
			 + " --outf <output file name>]");
	process.exit(0);
}

var ip_file = myArgs.inf;
var op_file = myArgs.outf;
var ks = myArgs.ks;
var boot2_enc_algo = myArgs.boot2_enc_algo;
var boot2_enc_key = myArgs.boot2_enc_key;
var boot2_nonce = myArgs.boot2_nonce;
var boot2_sign_algo = myArgs.boot2_sign_algo;
var boot2_prv_key = myArgs.boot2_prv_key;
var boot2_pub_key = myArgs.boot2_pub_key;
var fw_enc_algo = myArgs.fw_enc_algo;
var fw_dec_key = myArgs.fw_enc_key;
var fw_sign_algo = myArgs.fw_sign_algo;
var fw_hash_algo = myArgs.fw_hash_algo;
var fw_prv_key = myArgs.fw_prv_key;
var fw_pub_key = myArgs.fw_pub_key;

var align_size = 16;

/* Struct es_t elements */
var es_offset = 0;
var es_size = 570;
var es_oem_public_key_offset = 0;
var es_digital_sig_offset = 294;
var es_encrypted_img_len_offset = 550;
var es_nonce_offset = 554;

/* Struct hdr_t elements */
var hdr_offset = 570;
var hdr_size = 128;
var hdr_sh_offset = 80;
var hdr_boot2_magicCode_offset = 12;
var hdr_boot2_codeLen_offset = 84;
var hdr_boot2_CRCCheck_offset = 124;

/* Boot2 binary specific parameters */
var boot2_data_offset = 698;
var boot2_data_len = 0;
var boot2_len;

/* tlv_hdr structure elements */
var tlv_hdr_magic = new Uint32Array(1);
var tlv_hdr_len = new Uint32Array(1);
var tlv_hdr_crc = new Uint32Array(1);

/* tlv buffer parameters */
var tlv_buf_offset = 0;
var tlv_buf = new Buffer(2000);
tlv_buf.fill(0);
var is_tlv_added = false;

var boot2_buf = new Buffer(fs.readFileSync(ip_file), 'hex');

if (typeof boot2_enc_algo === "undefined" && typeof boot2_sign_algo === "undefined"
		&& typeof ks === "undefined") {
	console.log("No encryption or signing was asked for boot2 and no keystore is required");
	console.log("Doing nothing for boot2 image");
	var filename = get_outfile_name();
	fs.writeFileSync(filename, boot2_buf, 'hex');
	process.exit(0);
}

boot2_buf = Buffer.concat([boot2_buf, tlv_buf]);

/* Slicing boot2 es structure into a separate buffer */
boot2_es_buf = boot2_buf.slice(es_offset, es_size);
/* Slice boot2 hdr structure into a separate buffer */
boot2_hdr_buf = boot2_buf.slice(hdr_offset, hdr_offset + hdr_size);
/* Slice boot2 data into a separate buffer */
boot2_data_buf = boot2_buf.slice(boot2_data_offset, boot2_buf.length);
/* Data to be encrypted (boot2 hdr + boot2 data)*/
boot2_enc_buf = boot2_buf.slice(hdr_offset, boot2_buf.length);

function swap32(val) {
	return ((val & 0xFF) << 24)
		| ((val & 0xFF00) << 8)
		| ((val >> 8) & 0xFF00)
		| ((val >> 24) & 0xFF);
}

/* Initialize TLV header */
function tlv_init() {
	tlv_hdr_len = tlv_hdr_magic.BYTES_PER_ELEMENT +
		tlv_hdr_len.BYTES_PER_ELEMENT +
		tlv_hdr_crc.BYTES_PER_ELEMENT;
	tlv_hdr_magic = 0x534B4253;
	/* CRC is initialized to max tlv size(4K) */
	tlv_hdr_crc = 0x00001000;

	/* Write initial values to tlv buffer */
	tlv_buf.writeUInt32LE(tlv_hdr_magic, tlv_buf_offset, 4, 'hex');
	tlv_buf_offset += 4;
	tlv_buf.writeUInt32LE(tlv_hdr_len, tlv_buf_offset, 4, 'hex');
	tlv_buf_offset += 4;
	tlv_buf.writeUInt32LE(tlv_hdr_crc, tlv_buf_offset, 4, 'hex');
	tlv_buf_offset += 4;
}

function add_tlv_data(type, length, value, encoding) {
	is_tlv_added = true;
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
	var tlv_crc_buf = tlv_buf.slice(tlv_hdr_len, tlv_buf_offset);

	tlv_buf.writeUInt32LE(tlv_buf_offset, tlv_hdr_len_offset, 4, 'hex');
	tlv_buf.writeUInt32LE(wmcrc.crc32(tlv_crc_buf), tlv_hdr_crc_offset, 4, 'hex');
}

function generate_keystore() {
	/* Initialize tlv header */
	tlv_init();

	/* Add tlv data */
	if (typeof fw_sign_algo !== "undefined") {
		if (fw_sign_algo !== "RSA_SIGN") {
			console.error("Firmware Signing algorithm " + fw_sign_algo + " is not supported");
			process.exit(1);
		}
		add_tlv_data(0x20, 1, 0x01, 'hex');

		if (fw_hash_algo !== "SHA256_HASH") {
			console.error("Firmware Hashing algorithm " + fw_hash_algo + " is not supported");
			process.exit(1);
		}
		add_tlv_data(0x21, 1, 0x01, 'hex');

		if (typeof fw_pub_key === "undefined" ) {
			console.error("Specify public key for Firmware");
			process.exit(1);
		}
		var fw_prvKey = fs.readFileSync(fw_prv_key);
		/* Extract public key from private key of application firmware*/
		var key = new NodeRSA({b: 2048});
		key.importKey(fw_prvKey);
		var fw_pubKey = key.exportKey("pkcs8-public-der");
		add_tlv_data(0x24, fw_pubKey.length, fw_pubKey.toString('hex'));
	}

	if (typeof fw_enc_algo !== "undefined") {
		if (fw_enc_algo !== "AES_CTR_128_ENCRYPT") {
			console.error("Firmware Encryption algorithm " + fw_enc_algo + " is not supported");
			process.exit(1);
		}
		add_tlv_data(0x22, 1, 0x02, 'hex');

		if (typeof fw_dec_key === "undefined") {
			console.error("Specify encryption key for Firmware");
			process.exit(1);
		}
		var key = fw_dec_key.toString('hex');
		var len = fw_dec_key.length / 2;
		add_tlv_data(0x26, fw_dec_key.length / 2, fw_dec_key.toString('hex'));
	}

	if (typeof ks !== "undefined") {
		var ks_entries = new Array();
		var ks_entries = ks.split(",");

		for (var i = 0; i < ks_entries.length; i++) {
			var tlv_entry = new Array();
			var tlv_entry_type, tlv_entry_value, tlv_entry_len;
			var encoding;
			tlv_entry = ks_entries[i].split(":");
			tlv_entry_type = tlv_entry[0];
			if (tlv_entry[1] === 'hex') {
				tlv_entry_value = tlv_entry[2].toString('hex');
				tlv_entry_len = tlv_entry_value.length / 2;
			} else if (tlv_entry[1] === 'str') {
				tlv_entry_value = tlv_entry[2];
				tlv_entry_len = tlv_entry_value.length;
				encoding = 'utf8';
			} else if (tlv_entry[1] === 'dec') {
				tlv_entry_value = parseInt(tlv_entry[2]);
				tlv_entry_len = tlv_entry_value.length;
				encoding = 'decimal';
			}

			add_tlv_data(tlv_entry_type, tlv_entry_len, tlv_entry_value, encoding);
		}
	}

	/* Close tlv */
	tlv_close();
}

function encrypt_boot2() {
	var h = sjcl.codec.hex;
	var u = sjcl.codec.utf8String;
	var aes = new sjcl.cipher.aes(h.toBits(boot2_enc_key));
	var iv;

	boot2_enc_buf = boot2_enc_buf.slice(0, boot2_len);

	if (typeof boot2_nonce === "undefined") {
		/* Generate 12-digit random IV */
		iv = crypto.randomBytes(12).toString('hex');
	} else {
		iv = boot2_nonce;
	}
	
	var adata = "";
	var ivB = h.toBits(iv);
	var ad = h.toBits(adata);
	var pt = h.toBits(boot2_enc_buf.toString('hex'));
	var tlen = 128;
	var mic;

	var cipherText = sjcl.mode.ccm.encrypt(aes, pt, ivB, ad, tlen);

	cipherText = h.fromBits(cipherText);
	mic = cipherText.slice(cipherText.length - 32, cipherText.length);
	console.log("BOOT2 MIC: " + mic);
	boot2_buf.write(mic, es_size + boot2_len, 16, 'hex');
	boot2_enc_buf.write(cipherText.slice(0, cipherText.length - 32), 0, boot2_enc_buf.length, 'hex');

	/* Copy IV nonce to boot2 es header */
	boot2_es_buf.write(iv, es_nonce_offset, 12, 'hex');
	boot2_es_buf.writeUInt16LE(0x03, (es_nonce_offset + 13), 1, 'hex');
	boot2_es_buf.writeUInt32LE(boot2_len, es_encrypted_img_len_offset, 4, 'hex');
}

function sign_boot2() {
	/* Find hash of boot2 */
	var shasum = crypto.createHash('sha256');

	boot2_enc_buf = boot2_enc_buf.slice(0, boot2_len);
	shasum.update(boot2_enc_buf);
	var boot2_hash = shasum.digest('hex');
	console.log("BOOT2 HASH " + boot2_hash);

	/* Sign hash using RSA */
	var sign_data = new Buffer(boot2_hash, "hex");

	if (typeof boot2_pub_key === "undefined") {
		console.error("Boot2 public key for signing is not specified");
		process.exit(1);
	}
	if (typeof boot2_prv_key === "undefined") {
		console.error("Boot2 private key for signing is not specified");
		process.exit(1);
	}

	var prvKey = fs.readFileSync(boot2_prv_key);

	var digital_sig;
	var sign = forsake.sign(sign_data, prvKey);
	var tmp_buf = new Buffer(sign, 'base64');
	digital_sig = tmp_buf.toString('hex');
	console.log("BOOT2 SIGNATURE " + digital_sig);
	boot2_es_buf.write(digital_sig, es_digital_sig_offset, 256, 'hex');

	/* Convert Public key from PEM to DER using node-rsa */
	var key = new NodeRSA({b: 2048});
	key.importKey(prvKey);
	var pubKey = key.exportKey("pkcs8-public-der");
	boot2_es_buf.write(pubKey.toString('hex'), es_oem_public_key_offset, pubKey.length, 'hex');
	boot2_es_buf.writeUInt32LE(boot2_len, es_encrypted_img_len_offset, 4, 'hex');
}

function get_outfile_name() {
	if (typeof op_file !== "undefined")
		return op_file;

	var filename = "boot2";
	
	if (typeof boot2_enc_algo !== "undefined" || typeof boot2_sign_algo !== "undefined" ||
			typeof ks !== "undefined")
		filename = filename + ".";

	if (typeof ks !== "undefined" || typeof fw_enc_algo !== "undefined" ||
			typeof fw_sign_algo !== "undefined")
		filename = filename + "k";
	if (typeof boot2_enc_algo !== "undefined")
		filename = filename + "e";
	if (typeof boot2_sign_algo !== "undefined")
		filename = filename + "s";

	filename = filename + ".bin";

	return filename;
}

function write_boot2() {
	if (typeof boot2_enc_algo === "undefined") {
		/* Add 16 zeros for MIC */
		var zero_buf = new Buffer(16);
		zero_buf.fill(0);
		boot2_buf.write(zero_buf.toString('hex'), es_size + boot2_len, 16, 'hex');
	}
	/* Add 16 to length for MIC */
	boot2_len += 16;
	boot2_buf = boot2_buf.slice(0, es_size + boot2_len);
	var filename = get_outfile_name();
	fs.writeFileSync(filename, boot2_buf, 'hex');

	console.log("\r\nGenerated " + filename);
}

/* Validate boot2 */
var magic_code = boot2_hdr_buf.slice(hdr_boot2_magicCode_offset,
		hdr_boot2_magicCode_offset + 4);
if (magic_code != 'LVRM' && magic_code != 'MRVL') {
	console.error("Invalid Boot2.bin. Exiting.");
	process.exit(1);
}

if (typeof fw_enc_algo !== "undefined" || typeof fw_sign_algo !== "undefined" ||
		typeof ks !== "undefined") {
	generate_keystore();
}

boot2_len = boot2_hdr_buf.slice(hdr_boot2_codeLen_offset, hdr_boot2_codeLen_offset + 4);
var tmp = boot2_len.toString('hex');
tmp = parseInt(tmp, 16);
tmp = swap32(tmp);
boot2_len = tmp;

if (is_tlv_added === true) {
	/* Boot2 expects keystore on 16-byte boundary. Hence
	 * align length to 16-bytes before keystore is appended. Fill void
	 * with 0xff.  Boot2 layout is:
	 *
	 * | es_t | hdr_t | boot2 code | alignmt padding |
	 *   keystore | alignmt padding | codeSig | mic |
	 */
	var boot2_codeLen = boot2_len;

	/* Align boot2 length to 16 byte boundry */
	boot2_len = (boot2_codeLen + 4 + align_size - 1) & (~(align_size - 1));

	var padding = boot2_len - boot2_codeLen;

	/* Add padding */
	for (var i = 0; i < padding; i++) {
		boot2_data_buf.writeUInt32LE(0xFF, boot2_codeLen, 1, 'hex');
		boot2_codeLen++;
	}

	tlv_buf.copy(boot2_data_buf, boot2_len, 0, tlv_buf_offset);
	boot2_len += tlv_buf_offset;

	/* Align length to 16 byte boundary for AES-CCM. Fill void with 0xFF */
	var aligned_length = boot2_len;
	aligned_length = (boot2_len + 4 + align_size - 1) & (~(align_size - 1));
	aligned_length -= 4;

	padding = aligned_length - boot2_len;
	for (var i = 0; i < padding; i++) {
		boot2_data_buf.writeUInt32LE(0xFF, boot2_len, 1, 'hex');
		boot2_len++;
	}
	boot2_len = aligned_length;

	boot2_crc_buf = boot2_data_buf.slice(0, boot2_len);

	boot2_data_buf.writeUInt32LE(wmcrc.crc16(boot2_crc_buf), boot2_len, 4, 'hex');
	
	/* Flash section header */
	boot2_hdr_buf.writeUInt32LE(boot2_len, hdr_boot2_codeLen_offset, 4, 'hex');
	hdr_sh_buf = boot2_hdr_buf.slice(hdr_sh_offset, hdr_size - 4);

	boot2_hdr_buf.writeUInt32LE(wmcrc.crc16(hdr_sh_buf), hdr_size - 4, 4, 'hex');
}

boot2_len = hdr_size + boot2_len + 4;

if (typeof boot2_enc_algo !== "undefined") {
	if (boot2_enc_algo !== "AES_CCM_256_ENCRYPT") {
		console.error("Encryption method " + boot2_enc_algo + " is not supported");
		process.exit(1);
	} else
		encrypt_boot2();
}

if (typeof boot2_sign_algo !== "undefined") {
	if (boot2_sign_algo !== "RSA_SIGN") {
		console.error("Signing methond " + boot2_sign_algo + " is not supported");
		process.exit(1);
	} else
		sign_boot2();
}

write_boot2();
