var BASE_URL = "http://localhost:8080/"

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
                            var format = gateway.pformat();

                            var url = BASE_URL + "print." + format
                                    + "?base64=1"; //@todo o base 64 tem de ser bem visto e tenho de ver tamanho
                            jQuery.ajax({
                                        url : url,
                                        type : "post",
                                        data : result,
                                        contentType : "text/xml",
                                        success : function(data) {
                                            gateway.print(false, data);
                                        },
                                        error : function() {
                                            alert("Problem with file submission")
                                        }
                                    });
                        };

                        reader.readAsText(reference);
                    });
        });
