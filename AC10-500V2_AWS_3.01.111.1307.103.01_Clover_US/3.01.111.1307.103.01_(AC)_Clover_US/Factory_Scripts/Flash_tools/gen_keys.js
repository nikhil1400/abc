var myArgs = require('minimist')(process.argv.slice(2));

var crypto = require('crypto');
var fs = require('fs');

var count = myArgs.count;
var csv_db = myArgs.db;

if (myArgs.h === true || myArgs.help === true) {
	Usage();
}

function Usage() {
	console.log("Usage:\r\nnode gen_keys.js [--count <no of keys to be generated> --db <csv outfile name>]");
	process.exit(0);
}

if (typeof count === "undefined" || count == 1) {
	console.log("Generating single key and nonce...");
	count = 1;
} else {
	console.log("Generating " + count + " keys and nonces");
}

if (typeof csv_db === "undefined") {
	console.log("Creating key database in keys.csv");
	csv_db = "keys.csv";
} else {
	console.log("Creating key database in " + csv_db);
}

var csv_col_name = "boot2_enc_key\tmcufw_enc_key\tpsm_enc_key\tpsm_nonce\r\n";
var alpha_idx;
fs.writeFileSync(csv_db, csv_col_name);

for (var i = 0; i < count; i++) {
	/* Loop untill there is atleast one alphanumeric character in the
	 * key/nonce. This is required due to the fact that if csv file has all
	 * numeric characters, MS-excel automatically converts it into mathematical
	 * form, which transforms the key into inappropriate string */
	do {
		var aes_ccm_256_enc_key = crypto.randomBytes(32).toString('hex');
		alpha_idx = aes_ccm_256_enc_key.search(/[a-f]/g);
	} while (alpha_idx === -1)
	do {
		var aes_ccm_256_nonce = crypto.randomBytes(12).toString('hex');
		alpha_idx = aes_ccm_256_nonce.search(/[a-f]/g);
	} while (alpha_idx === -1)
	do {
		var aes_ctr_128_enc_key = crypto.randomBytes(16).toString('hex');
		alpha_idx = aes_ctr_128_enc_key.search(/[a-f]/g);
	} while (alpha_idx === -1)
	do {
		var aes_ctr_128_nonce = crypto.randomBytes(16).toString('hex');
		alpha_idx = aes_ctr_128_nonce.search(/[a-f]/g);
	} while (alpha_idx === -1)
	do {
		var aes_ctr_128_enc_key_psm = crypto.randomBytes(16).toString('hex');
		alpha_idx = aes_ctr_128_enc_key_psm.search(/[a-f]/g);
	} while (alpha_idx === -1)
	do {
		var aes_ctr_128_nonce_psm = crypto.randomBytes(16).toString('hex');
		alpha_idx = aes_ctr_128_nonce_psm.search(/[a-f]/g);
	} while (alpha_idx === -1)

	fs.appendFileSync(csv_db, aes_ccm_256_enc_key + "\t");
//	fs.appendFileSync(csv_db, aes_ccm_256_nonce + "\t");
	fs.appendFileSync(csv_db, aes_ctr_128_enc_key + "\t");
//	fs.appendFileSync(csv_db, aes_ctr_128_nonce + "\t");
	fs.appendFileSync(csv_db, aes_ctr_128_enc_key_psm + "\t");
	fs.appendFileSync(csv_db, aes_ctr_128_nonce_psm + "\r\n");
}

