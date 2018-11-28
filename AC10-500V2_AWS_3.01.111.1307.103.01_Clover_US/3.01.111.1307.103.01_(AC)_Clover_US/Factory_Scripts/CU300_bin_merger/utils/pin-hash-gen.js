
var argv = process.argv.slice(2);

if (argv.length < 6 || argv[0] === "-h" || argv[0] === "--help") {
	console.error("Usage: node pin-hash-gen.js -p pin -c hash-method -n  name");
	console.error("Supported hash methods: sha1, sha256, sha512, md5");
	process.exit(1);
}

var pin_str = "", hash_method_str = "", name_str = "";
var pin, hash_method;

for (var i = 0; i < argv.length; i++) {
	if (argv[i] === "-p") {
		pin_str = argv[i+1];
		i++;
	}
	if (argv[i] === "-c") {
		hash_method_str = argv[i+1];
		i++;
	}
	if (argv[i] === "-n") {
		name_str = argv[i+1];
		i++;
	}
}

if (typeof pin_str === "undefined" || pin_str.match(/[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9]/) === null || pin_str.match(/[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9]/).toString().length !== 10) {
	console.error("Invalid PIN. PIN must be in xxx-xx-xxx format.");
	process.exit(3);
}

//console.log("# Pin " + pin_str);

var crypto = require('crypto');

var temp = pin_str.replace(/-/g,'');
var data = crypto.createHash(hash_method_str).update(temp).digest("hex");

console.log(name_str+"="+data);
