var myArgs = require('minimist')(process.argv.slice(2));

if (myArgs.h === true || myArgs.help === true) {
	Usage();
}

function Usage() {
	console.log("Usage:\r\nnode gen_keypair.js [--outdir <output dir> --count <no. of keypairs to be generated> --db <CSV output>]");
	process.exit(0);
}

var NodeRSA = require('node-rsa');
var fs = require('fs');

var outdir = myArgs.outdir;
var count = myArgs.count;
var csv_db = myArgs.db;

if (typeof outdir === "undefined") {
	console.log("No output directory specified. Storing keys in current directory");
	outdir = __dirname;
}

if (typeof count === "undefined" || count === 1) {
	console.log("Generating 1 keypair...");
	count = 1;
} else {
	console.log("Generating " + count + " keypairs...");
}

for (var i = 1; i <= count; i++) {
	var boot2_key = new NodeRSA({b: 2048});
	var fw_key = new NodeRSA({b: 2048});

	var boot2_prv_key = boot2_key.exportKey("pkcs1-private-pem");
	var boot2_pub_key = boot2_key.exportKey("pkcs8-public-pem");
	var fw_prv_key = fw_key.exportKey("pkcs1-private-pem");
	var fw_pub_key = fw_key.exportKey("pkcs8-public-pem");

	var boot2_prv_filename = outdir + "/boot2-prvKey-" + i + ".pem";
	var boot2_pub_filename = outdir + "/boot2-pubKey-" + i + ".pem";
	var fw_prv_filename = outdir + "/mcufw-prvKey-" + i + ".pem";
	var fw_pub_filename = outdir + "/mcufw-pubKey-" + i + ".pem";

	fs.writeFileSync(boot2_prv_filename, boot2_prv_key);
	fs.writeFileSync(boot2_pub_filename, boot2_pub_key);
	fs.writeFileSync(fw_prv_filename, fw_prv_key);
	fs.writeFileSync(fw_pub_filename, fw_pub_key);
}

if (typeof csv_db === "undefined") {
	csv_db = outdir + "/keypairs.csv";
	console.log("No CSV specified. Storing keypair database in " + csv_db);
} else {
	csv_db = outdir + "/" + csv_db;
	console.log("Storing keypair database in " + csv_db);
}

var csv_col_name = "boot2_prv_key\tboot2_pub_key\tmcufw_prv_key\tmcufw_pub_key\r\n";
fs.writeFileSync(csv_db, csv_col_name);

for (var i = 1; i <= count; i++) {
	var boot2_prv_filename = outdir + "/boot2-prvKey-" + i + ".pem";
	var boot2_pub_filename = outdir + "/boot2-pubKey-" + i + ".pem";
	var fw_prv_filename = outdir + "/mcufw-prvKey-" + i + ".pem";
	var fw_pub_filename = outdir + "/mcufw-pubKey-" + i + ".pem";

	var csv_row = boot2_prv_filename + "\t" + boot2_pub_filename + "\t" + fw_prv_filename + "\t" + fw_pub_filename + "\r\n";
	fs.appendFileSync(csv_db, csv_row);
}
