var BASE_URL = "http://print.bemisc.com/";

jQuery(document).ready(function() {
    var body = jQuery("body");
    var file = jQuery("#file", body);

    file.bind("change", function() {
        var element = jQuery(this);
        var _file = element[0];
        var reference = _file.files[0];

        var reader = new FileReader();
        reader.onload = function(event) {
            var result = event.target.result;
            var gateway = document.getElementById("colony-gateway");
            print(gateway, result);
        };

        reader.readAsText(reference);
    });
});

var print = function(gateway, result) {
    // uses the gateway refernce to retrieve the format to be used
    // for the current context and start the data map with the base
    // 64 reference set to valid so that is safe to handle data
    var format = gateway.pformat();
    var data = {
        base64: 1
    };

    // in case the target format is pdf extra values must be added
    // to the data map containin the size of the paper provided by
    // the default printer (for correct pdf generation)
    if (format === "pdf") {
        sizes(gateway, data);
    }

    // converts the data map that contains extra arguments into
    // a series of key value associations that are going to be
    // appended to the current url
    var extra = serialize(data);

    // creates the complete url that is going to be used taking
    // into account the target print format and the extra parameters
    // that are going to be used as get parameters, then runs the
    // remote call to convert the provided printing xml into the
    // binie/pdf code that is going to be used for printing
    var url = BASE_URL + "print." + format + extra;
    jQuery.ajax({
        url: url,
        type: "post",
        data: result,
        contentType: "text/xml",
        success: function(data) {
            gateway.print(false, data);
        },
        error: function() {
            alert("Problem with file submission");
        }
    });
};

var sizes = function(gateway, data) {
    // retrieves the complete set of device specifications
    // for the current system and sets the intial value of
    // the default device variable as unset
    var devices = gateway.pdevices();
    var defaultDevice = null;

    // iterates over all the (printing) devices in the system
    // to try to "find" the one that's the default
    for (var index = 0; index < devices.length; index++) {
        var device = devices[index];
        if (!device.isDefault) {
            continue;
        }
        defaultDevice = device;
        break;
    }

    // in case no default device is found must return immediately
    // nothing to be set for the current situation
    if (!defaultDevice) {
        return;
    }

    // updates the data structure with the device with and length
    // for the defined paper size
    data.width = defaultDevice.width;
    data.height = defaultDevice.length;
};

var serialize = function(data) {
    var buffer = ["?"];
    var isFirst = true;

    for (var key in data) {
        var value = data[key];
        if (isFirst) {
            isFirst = false;
        } else {
            buffer.push("&");
        }
        var keyS = encodeURIComponent(String(key));
        var valueS = encodeURIComponent(String(value));
        buffer.push(keyS + "=" + valueS);
    }

    var result = buffer.join("");
    return result;
};
