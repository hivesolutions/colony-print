var BASE_URL = "http://localhost:8080/"

jQuery(document).ready(function() {
            var body = jQuery("body");
            var file = jQuery("#file", body);

            file.bind("change", function() {
                        var element = jQuery(this);
                        var _file = element[0];
                        var document = _file.files[0];

                        var reader = new FileReader();
                        reader.onload = function(event) {
                            var result = event.target.result;

                            var url = BASE_URL + "print.binie"; //@todo take into account os
                            jQuery.ajax({
                                        url : url,
                                        type : "post",
                                        data : {
                                            base64 : "1"
                                        },
                                        contentType : "text/xml",
                                        success : function(data) {
                                            console.info(data);
                                        },
                                        error : function() {
                                            console.info("ERROR")
                                        }
                                    });
                        };

                        reader.readAsBinaryString(document);
                    });
        });

function version() {
    try {
        var gateway = document.getElementById("colony-gateway");
        alert(gateway.version());
    } catch (exception) {
        alert(exception);
    }
}

function pformat() {
    try {
        var gateway = document.getElementById("colony-gateway");
        alert(gateway.pformat());
    } catch (exception) {
        alert(exception);
    }
}

function pdevices() {
    try {
        var gateway = document.getElementById("colony-gateway");
        var devices = gateway.pdevices();
        var devicesS = "";
        var isFirst = true;
        for (var index = 0; index < devices.length; index++) {
            var device = devices[index];
            devicesS += isFirst ? "" : "\n"
            devicesS += device.name + " - " + (device.media || "N/A");
            isFirst = false;
        }
        alert(devicesS);
    } catch (exception) {
        alert(exception);
    }
}

function foo() {
    try {
        var gateway = document.getElementById("colony-gateway");
        alert(gateway.foo());
    } catch (exception) {
        alert(exception);
    }
}

function callback() {
    try {
        var gateway = document.getElementById("colony-gateway");
        gateway.callback(function(message) {
                    alert(message);
                });
    } catch (exception) {
        alert(exception);
    }
}

function _alert() {
    try {
        var gateway = document.getElementById("colony-gateway");
        gateway.alert("Hello World :: Olá Mundo");
    } catch (exception) {
        alert(exception);
    }
}

function _print() {
    try {
        var gateway = document.getElementById("colony-gateway");
        var format = gateway.pformat();
        switch (format) {
            case "binie" :
                gateway.print(true, HELLO_WORD_BINIE_B64);
                break;

            case "pdf" :
                gateway.print(true, HELLO_WORD_PDF_B64);
                break;

            default :
                break;
        }
    } catch (exception) {
        alert(exception);
    }
}
