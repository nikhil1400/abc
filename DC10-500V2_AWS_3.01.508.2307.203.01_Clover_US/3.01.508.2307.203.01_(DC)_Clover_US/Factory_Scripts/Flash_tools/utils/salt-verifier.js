var srp=require('srp');

var argv = process.argv.slice(2);

function randomUInt8() {
	return Math.floor((Math.random() * 256));
}

function hexSeqtoBuf(hexseq) {
	var len = Math.floor((hexseq.length + 1) / 2 );
	var buf = new Buffer(len);

	for (var i = 0; i < len; i++) {
		var tmp = "0x"+hexseq[2*i]+""+hexseq[2*i+1];
		buf[i] = parseInt(tmp);
	}
	return buf;
}

if (argv.length === 0 || argv[0] === "-h" || argv[0] === "--help") {
	console.error("Usage: node salt-verifier -p pin [-s salt]");
	process.exit(1);
}

var pin_str = "", salt_str = "";
var pin, salt;

for (var i = 0; i < argv.length; i++) {
	if (argv[i] === "-p") {
		pin_str = argv[i+1];
		i++;
	}
	if (argv[i] === "-s") {
		salt_str = argv[i+1];
		i++;
	}
}

if (typeof pin_str === "undefined" || pin_str.match(/[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9]/) === null || pin_str.match(/[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9]/).toString().length !== 10) {
	console.error("Invalid PIN. PIN must be in xxx-xx-xxx format.");
	process.exit(3);
}

if (salt_str !== "") {
	if (typeof salt_str === "undefined" || salt_str.match(/[0-9a-fA-F]+/g).toString().length !== 32) {
		console.error("Invalid salt");
		process.exit(2);
	}
	salt = hexSeqtoBuf(salt_str);
} else {
	salt = new Buffer(16);
	for (var i = 0; i < 16; i++) {
		salt[i] = randomUInt8();
	}
}
//console.log("# Pin " + pin_str);
var params = srp.params["3072"];
params.hash = 'sha512'; /* Default hash for 3072 is sha256; we need to override */

var identity = new Buffer("Pair-Setup");
var pass = new Buffer(pin_str);

var verifier = srp.computeVerifier(params, salt, identity, pass);
console.log("salt=:"+salt.toString('hex'));
console.log("verifier=:"+verifier.toString('hex'));
