var myArgs = require('minimist')(process.argv.slice(2));
var fs = require('fs');
var execSync = require('execSync');
var path = require('path');

if (myArgs.h === true || myArgs.help === true ) {
	console.log("Usage:\r\nnode mfg-creator.js --db <CSV file> [--from <from line> --to <to line>] --cfg <config file> --outdir <output dir>");
	process.exit(0);
}

if (typeof myArgs.db === "undefined" || typeof myArgs.cfg === "undefined" || typeof myArgs.outdir === "undefined") {
	console.error("Usage:\r\nnode mfg-creator.js --db <CSV file> [--from <from line> --to <to line>] --cfg <config file> --outdir <output dir>");
	process.exit(1);
}

var LineByLineReader = require('line-by-line'),
	    lr = new LineByLineReader(myArgs.db, {skipEmptyLines: true});


var nr_line = 0;
var psm_create_exec, gen_secure_boot2_exec, gen_app_fw_exec, boot2_bin, mcufw_bin, mfg_encrypt;
var id_column_index = -1;

var var_config = new Array();
var names_config = new Array();

var OUT_DIR=myArgs.outdir;
if (OUT_DIR.match(/(.*)\/$/) === null) {
	OUT_DIR += "/";
}

/* Hack: line-by-line fails to parse lingle column csv with no newline at the end */
fs.appendFileSync(myArgs.db, '\n');

var lr_cfg = new LineByLineReader(myArgs.cfg, {skipEmptyLines: true});
lr.pause();
lr_cfg.on('error', function(err) {
	console.error(err);
	process.exit(1);
});

lr_cfg.on('line', function(line) {
	if (line.indexOf("#") === 0) {
		return;
	}

	if (line.indexOf("=") !== -1) {
		var components = line.split("=");
		if (components[0] == "PSM_CREATE") psm_create_exec=components[1];
		if (components[0] == "GEN_SECURE_BOOT2") gen_secure_boot2_exec=components[1];
		if (components[0] == "GEN_APP_FW") gen_app_fw_exec=components[1];
		if (components[0] == "BOOT2_IMG") boot2_bin=components[1];
		if (components[0] == "MCUFW_IMG") mcufw_bin=components[1];
		if (components[0] == "MFG_ENCRYPT") mfg_encrypt=components[1];
	}

	var pattern = /^([a-zA-Z0-9_\.]+) \((.*)\)/;
	var match = pattern.exec(line);

	if (match === null) return;
	var options = match[2].split(",");
	var name = match[1];

	var_config[name] = new Object();
	for (var j = 0; j < options.length; j++) {
		switch(options[j]) {
		  case "id":
			  var_config[name].id = true;
			  break;
		  case "discard":
			  var_config[name].discard = true;
			  break;
		  case "hexdata":
			  var_config[name].hexdata = true;
			  break;
		}

		if (options[j].indexOf("process:") === 0) {
			var_config[name].process = true;
			var_config[name].exec = new Array();
			var exec_params = options[j].split(":");
			for (var k = 1; k < exec_params.length; k++) {
				var_config[name].exec[k-1] = exec_params[k];
			}	
		}

		if (options[j].indexOf("fw:") === 0) {
			var_config[name].fw = true;
			var datatype = options[j].split(":");
			var_config[name].datatype = datatype[1];
		}

		if (options[j].indexOf("boot2:") === 0) {
			var_config[name].boot2 = true;
			var datatype = options[j].split(":");
			var_config[name].datatype = datatype[1];
		}

		if (options[j].indexOf("ks:") === 0) {
			var_config[name].ks = true;
			var datatype = options[j].split(":");
			var_config[name].datatype = datatype[1];
		}
	}
});

lr_cfg.on('end', function(){
	lr.resume();
});

function build_config_db(names) {
	for (var i = 0; i < names.length; i++) {
		if (typeof var_config[names[i]] !== "undefined") {
			names_config[i] = var_config[names[i]];
			names_config[i].name = names[i];
			if (typeof var_config[names[i]].id !== "undefined" && var_config[names[i]].id === true) {
			   id_column_index = i;
			}
		} else {
			names_config[i] = new Object();
			names_config[i].name = names[i];
		}
	}
	console.log("Using configuration:");
	console.dir(names_config);
	console.log("");
}

function process_value_using_exec(value, exec_env)
{
	var cmdline = exec_env[0];

	for (var i = 1; i < exec_env.length; i++) {
		if (exec_env[i] === '$value')
			cmdline = cmdline + " " + value;
		else
			cmdline = cmdline + " " + exec_env[i];
	}
	var v = execSync.exec(cmdline);
	if (v.code !== 0 || (typeof v.stderr !== "undefined" && v.stderr.length > 0)) {
		console.error("Error occured to execute process.");
		console.error("Commandline: " + cmdline);
		console.error("Error: " + v.stderr);
		process.exit(1);
	}
	return v.stdout;
}

function process_values(values, nr) {
	var cfg_file_name;
	var id = nr;
	var boot2_arg_idx = 0;
	var boot2_ks_idx = 0;
	var app_fw_arg_idx = 0;
	var psm_enc_key_idx = -1;
	var psm_nonce_idx = -1;
	var boot2_cmd_par = new Array();
	var boot2_ks = new Array();
	var app_fw_cmd_par = new Array();
	
	if (id_column_index !== -1) {
		id = values[id_column_index];
	}
	cfg_file_name = OUT_DIR + "./cfg-" + id +".cfg";

	var fd = fs.openSync(cfg_file_name, 'w');

	for (var i = 0; i < values.length; i++) {
		if (typeof names_config[i].discard !== "undefined" && names_config[i].discard === true)
			continue;
	
		if (typeof names_config[i].process !== "undefined" && names_config[i].process === true) {
			var processed_output = process_value_using_exec(values[i], names_config[i].exec);
			fs.writeSync(fd, Buffer(processed_output), 0, processed_output.length, null);
		   	continue;	
		}
		if (typeof names_config[i].fw !== "undefined" && names_config[i].fw === true) {
			if (values[i] != '') {
				app_fw_cmd_par[app_fw_arg_idx++] = "--fw_" + names_config[i].datatype;
				app_fw_cmd_par[app_fw_arg_idx++] = " " + values[i] + " ";
			}
			continue;
		}
		if (typeof names_config[i].boot2 !== "undefined" && names_config[i].boot2 === true) {
			if (values[i] != '') {
				boot2_cmd_par[boot2_arg_idx++] = "--boot2_" + names_config[i].datatype;
				boot2_cmd_par[boot2_arg_idx++] = " " + values[i] + " ";
			}
			continue;
		}
		if (typeof names_config[i].ks !== "undefined" && names_config[i].ks === true) {
			if (values[i] != '') {
				if (names_config[i].datatype === "psm_enc_key") {
					boot2_ks[boot2_ks_idx++] = "97:hex:" + values[i] + ",";
					psm_enc_key_idx = i;
				}
				if (names_config[i].datatype === "psm_nonce") {
					boot2_ks[boot2_ks_idx++] = "98:hex:" + values[i] + ",";
					psm_nonce_idx = i;
				}
			}
			continue;
		}
		fs.writeSync(fd, Buffer(names_config[i].name), 0, names_config[i].name.length, null);
		if (typeof names_config[i].hexdata !== "undefined" && names_config[i].hexdata === true) {
			fs.writeSync(fd, Buffer("=:"), 0, 2, null);
		} else {
			fs.writeSync(fd, Buffer("="), 0, 1, null);
		}
		fs.writeSync(fd, Buffer(values[i]), 0, values[i].length, null);
		fs.writeSync(fd, Buffer("\n"), 0, 1, null);
	}
	fs.closeSync(fd);
	console.log("[CFG] Generated " + cfg_file_name);
	
	if (boot2_arg_idx != 0) {
		var boot2_file_name = OUT_DIR + "boot2-" + id + ".bin";
		var gen_boot2_cmdline = gen_secure_boot2_exec + " " + app_fw_cmd_par + boot2_cmd_par +
			"--inf " + boot2_bin + " --outf " + boot2_file_name;
		gen_boot2_cmdline = gen_boot2_cmdline.replace(/,/g, '');
		if (boot2_ks_idx != 0)
			gen_boot2_cmdline += " --ks " + boot2_ks;
		gen_boot2_cmdline = gen_boot2_cmdline.replace(/,$/, '');
		gen_boot2_cmdline = gen_boot2_cmdline.replace(/:,/g, ':');
		gen_boot2_cmdline = gen_boot2_cmdline.replace(/,,/g, ',');

		var v = execSync.exec(gen_boot2_cmdline);
		if (v.code !== 0 || (typeof v.stderr !== "undefined" && v.stderr.length > 0)) {
			console.error("Error occured in secure-boot2-generator.");
			console.error("Commandline: "+gen_boot2_cmdline);
			console.error("Error: "+v.stderr);
		} else
			console.log("[BOOT2] Generated " + boot2_file_name);
	}

	if (app_fw_arg_idx != 0) {
		var app_fw_file_name = OUT_DIR + path.basename(mcufw_bin, '.bin') + "-" + id + ".bin";
		var gen_app_fw_cmdline = gen_app_fw_exec + " " + app_fw_cmd_par + "--inf " + mcufw_bin +
			" --outf " + app_fw_file_name;
		gen_app_fw_cmdline = gen_app_fw_cmdline.replace(/,/g, '');
		var v = execSync.exec(gen_app_fw_cmdline);
		if (v.code !== 0 || (typeof v.stderr !== "undefined" && v.stderr.length > 0)) {
			console.error("Error occured in application-firmware-generator.");
			console.error("Commandline: "+gen_app_fw_cmdline);
			console.error("Error: "+v.stderr);
		} else
			console.log("[MCUFW] Generated " + app_fw_file_name);
	}

	var mfg_file_name = OUT_DIR + "./mfg-" + id + ".bin";
	var psm_create_cmdline = psm_create_exec + " --cfg " + cfg_file_name + " --out " + mfg_file_name;
	if ((mfg_encrypt === "1") && (psm_enc_key_idx != -1) && (psm_nonce_idx != -1))
		psm_create_cmdline += " --psm_enc_key " + values[psm_enc_key_idx] + " --psm_nonce " + values[psm_nonce_idx];
	var v = execSync.exec(psm_create_cmdline);
	if (v.code !== 0 || (typeof v.stderr !== "undefined" && v.stderr.length > 0)) {
		console.error("Error occured in psm-creator.");
		console.error("Commandline: "+psm_create_cmdline);
		console.error("Error: "+v.stderr);
		process.exit(1);
	}
	console.log("[MFG] Generated " + mfg_file_name);
}

lr.on('line', function (line) {
	if (nr_line === 0) {
		var names = line.split(",");
		console.log("Variable Names Parsed:");
		console.dir(names);
		console.log("");
		build_config_db(names);
	} else {
		if (typeof myArgs.from !== "undefined") {
			if (nr_line < myArgs.from) {
				nr_line++;
				return;
			}
		}
		if (typeof myArgs.to !== "undefined") {
			if (nr_line > myArgs.to) {
				nr_line++;
				return;
			}	
		}

		var values = line.split(",");
		/* Skip empty lines */
		for (var i = 0; i < values.length; i++) {
			if (values[i])
				break;
		}
		if (i == values.length) {
			nr_line++;
			return;
		}

		/* Process the values now */
		process_values(values, nr_line);
	}
	nr_line++;		
});

lr.on('end', function () {
	console.log("Done");
});

