var myArgs = require('minimist')(process.argv.slice(2));

var Buffer = require('buffer').Buffer;
var fs = require('fs');

if (myArgs.h === true || myArgs.help === true) {
	Usage();
	process.exit(0);
}

function Usage() {
	console.log("Usage:\r\nnode gen_wifi_fw.js --inf <input file> [--outf <output file>]");
}

var ip_file = new Buffer(fs.readFileSync(myArgs.inf), 'hex');
var op_file = myArgs.outf;

var magic = 0x57464c57;
var buf = new Buffer(8);

buf.writeUInt32LE(magic, 0, 4, 'hex');
buf.writeUInt32LE(ip_file.length, 4, 4, 'hex');

if (typeof op_file === "undefined") {
	op_file = "a.bin";
}

fs.writeFileSync(op_file, buf, 'hex');
fs.appendFileSync(op_file, ip_file, 'hex');
console.log("Generated " + op_file);
