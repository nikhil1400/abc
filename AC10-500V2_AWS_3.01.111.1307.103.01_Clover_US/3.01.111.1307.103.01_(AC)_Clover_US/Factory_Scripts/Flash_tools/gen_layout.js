var myArgs = require('minimist')(process.argv.slice(2));

var Buffer = require('buffer').Buffer;
var fs = require('fs');
var wmcrc = require('./utils/lib/wmcrc.js');

if (myArgs.h === true || myArgs.help == true) {
	Usage();
	process.exit(0);
}

function Usage() {
	console.log("Usage:\r\nnode gen_layout.js --inf <input file> [--outf <output file>]");
}

var ip_file = myArgs.inf;
var op_file = myArgs.outf;
var ip_buf = new Buffer(fs.readFileSync(ip_file));

var pt_magic_32, pt_ver_16, pt_entries_no_16, pt_gen_level_32, pt_crc_32;
var pe_type_8, pe_device_8, pe_name, pe_start_32, pe_size_32, pe_gen_level_32;
var pe_array = new Array();
var pt_buf = new Buffer(16, 'hex');
var pe_buf = new Buffer(1024, 'hex');
pt_buf.fill(0);
pe_buf.fill(0);
var parts_no = 0;

var FC_COMP_BOOT2 = 0;
var FC_COMP_FW = 1;
var FC_COMP_WLAN_FW = 2;
var FC_COMP_FTFS = 3;
var FC_COMP_PSM = 4;
var FC_COMP_USER_APP = 5;

var LineByLineReader = require('line-by-line'),
	lr = new LineByLineReader(myArgs.inf, {skipEmptyLines: true});

/* Read layout.txt and populate partition entry variables */

lr.on('error', function(err) {
	console.error(err);
	process.exit(1);
});

lr.on('line', function(line) {
	if (line.indexOf("#") === 0) {
		return;
	}

	var components = line.split(/[ \(\t\)]+/);
	pe_array[parts_no] = new Object();
	pe_array[parts_no].gen_level = 1;
	pe_array[parts_no].start = components[1];
	pe_array[parts_no].size = components[2];
	pe_array[parts_no].device = components[3];
	pe_array[parts_no].name = components[4];

	if (components[0] === "FC_COMP_BOOT2")
		pe_array[parts_no].type = FC_COMP_BOOT2;
	else if (components[0] === "FC_COMP_FW")
		pe_array[parts_no].type = FC_COMP_FW;
	else if (components[0] === "FC_COMP_WLAN_FW")
		pe_array[parts_no].type = FC_COMP_WLAN_FW;
	else if (components[0] === "FC_COMP_FTFS")
		pe_array[parts_no].type = FC_COMP_FTFS;
	else if (components[0] === "FC_COMP_PSM")
		pe_array[parts_no].type = FC_COMP_PSM;
	else if (components[0] === "FC_COMP_USER_APP")
		pe_array[parts_no].type = FC_COMP_USER_APP;

	parts_no++;

});

lr.on('end', function(){
	lr.resume();
	populate_ptable();
	populate_pentry();
});

function populate_ptable() {
	/* Partition table magic no. */
	pt_buf.write('WMPT', 0, 4);
	/* Partition table version */
	pt_buf.writeUInt16LE(0x01, 4, 2, 'hex');
	/* No. of entries in partition table */
	pt_buf.writeUInt16LE(parts_no, 6, 2, 'hex');
	/* Partition table generation level */
	pt_buf.writeUInt32LE(0x00, 8, 4, 'hex');
	var pt_crc_buf = pt_buf.slice(0, 12);
	/* Partition table CRC */
	pt_buf.writeUInt32LE(wmcrc.crc32(pt_crc_buf), 12, 4, 'hex');
}

function populate_pentry() {
	var pentry_offset = 0;
	for (var i = 0; i < parts_no; i++) {
		pe_buf.writeUInt32LE(pe_array[i].type, pentry_offset, 1, 'hex');
		pentry_offset += 1;
		pe_buf.writeUInt32LE(pe_array[i].device, pentry_offset, 1, 'hex');
		pentry_offset += 1;
		pe_buf.write(pe_array[i].name, pentry_offset, 10);
		pentry_offset += 10;
		pe_buf.writeUInt32LE(pe_array[i].start, pentry_offset, 4, 'hex');
		pentry_offset += 4;
		pe_buf.writeUInt32LE(pe_array[i].size, pentry_offset, 4, 'hex');
		pentry_offset += 4;
		pe_buf.writeUInt32LE(pe_array[i].gen_level, pentry_offset, 4, 'hex');
		pentry_offset += 4;
	}
	var pe_crc_buf = pe_buf.slice(0, pentry_offset);
	pe_buf.writeUInt32LE(wmcrc.crc32(pe_crc_buf), pentry_offset, 4, 'hex');
	pe_buf = pe_buf.slice(0, pentry_offset + 4);
	if (typeof op_file === "undefined") {
		op_file = "a.bin";
	}
	fs.writeFileSync(op_file, pt_buf, 'hex');
	fs.appendFileSync(op_file, pe_buf, 'hex');
	console.log("Generated " + op_file);
}
