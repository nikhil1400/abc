var nr_pins;
var prohibited_pins = new Array("000-00-000", "111-11-111", "222-22-222", "333-33-333", "444-44-444", "555-55-555", "666-66-666", "777-77-777", "888-88-888", "999-99-999", "123-45-678", "876-54-321");

function randomDigit() {
	return Math.floor((Math.random() * 10));
}

argv_pins = process.argv.slice(2)[0];

if (typeof argv_pins === "undefined") {
	nr_pins = 1;
} else if (isNaN(argv_pins)) {
	console.error("Usage: node homekit-pingen.js [<number>]");
	process.exit(1);
} else {
	nr_pins = argv_pins;
}

var i, pin, valid_pin;
var fs = require('fs');
i = 0;
while (i < nr_pins) {
	pin = "";
	for (var j = 0; j < 8; j++) {
		pin = pin + "" + randomDigit();
		if (j == 2 || j == 4)
			pin = pin + "-";	
	}
	
	valid_pin = true;
	for (var j = 0; j < prohibited_pins.length; j++) {
		if (prohibited_pins[j] === pin) {
			valid_pin = false;
			break;
		}
	}

	if (!valid_pin)
		continue;
	pin = pin + "\n";
	if (i == 0) {
		fs.writeFile("./temp/HKPins.txt", pin, function(err){
			if(err){
				return console.log(err);
			}
			console.log("The file was saved!");
		});
	}
	else {
		fs.appendFile("./temp/HKPins.txt", pin, function(err){
			if(err){
				return console.log(err);
			}
			console.log("The file was attached!");
		});
		
	}
	i++;
	console.log(pin);
}