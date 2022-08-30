(function( aob, $, undefined ) {
    //Private Property
    var aob_list = [];
    var current_process = "";

    //Public Property
    aob.test = "Bacon Strips";

    //Public Method
    aob.ready = function() {
        $("#aob_search_status").hide()
        $("#aob_search_names").hide()
        $("#aob_run").prop("disabled", true);
        $("#aob_search_status").hide()
        $("#aob_search_type_value").hide()
        $("#aob_search_done_initial").hide()
        $("#aob_search_no_results").hide()
        $("#aob_search_done").hide()
        hide_result_button()
        $("#aob_results_text").hide()
        get_aob_status();
    };

    aob.aob_search_type_changed = function() {
        check_value_type();
    };

    aob.on_process_changed = function(process) {
        current_process = process
        check_run();
    };

    aob.aob_search_address_changed = function() {
        check_run();
    }

    aob.aob_search_name_selected = function() {
        var value = $('#aob_search_names  option:selected').text();
        $('#aob_search_name').val(value);
        aob.aob_search_name_changed()
    };

    aob.aob_search_name_changed = function() {
        hide_result_button();
        check_valid_aobs();
        if (aob_list.indexOf($('#aob_search_name').val()) != -1) {
          $('#aob_search_names').val($('#aob_search_name').val());
        } else {
          $('#aob_search_names').val('_null');
        }
        check_results();
        check_run();
    };

    aob.aob_upload_file_changed = function(file) {
        if (file.size > 400000) {
            ons.notification.toast('File must be under 400KB', { timeout: 2000, animation: 'fall' })
            return
        } else if (file.size <= 20) {
            ons.notification.toast('AOB file is too small.', { timeout: 2000, animation: 'fall' })
            return
        }
        var reader = new FileReader();
        reader.readAsText(file, 'UTF-8');
        reader.onload = function(event) {
            var result = event.target.result;
            var fileName = file.name;
            $.post('/aob', { "type": "AOB_UPLOAD_FILE", data: result, name: fileName }, on_aob_upload_complete);
        }
    }

    aob.result_switch_changed = function(event) {
        if (event.value) {
            $("#aob_results_text").show();
        } else {
            $("#aob_results_text").hide();
        }
    }

    aob.download_aob = function() {
        var name = $("#aob_search_name").val().trim()+'.aob';
        var text = $("#aob_results_text textarea").val();
        _download(name, text)
    }

    aob.run_aob = function() {
        //var name = $('#aob_checker_names  option:selected').text();
        var name = $("#aob_search_name").val().trim();
        var proc = $("select[class='process_control']").val();

        var address = $("#aob_search_address").val().trim();
        var value = $("#aob_search_value").val().trim();

        var size = $("#aob_search_size").val().trim();
        var range = $("#aob_search_range").val().trim();

        var val_or_address = $("#aob_address_or_value option:selected").val();

        on_search_started();
        $.ajax
        ({
            url: '/aob',
            data: {"type": "AOB_SEARCH", "name": name, "process": proc, "address": address, "value": value, "size": size, "range": range, "is_value": val_or_address == "value"},
            type: 'post',
            success: function(result)
            {
                //catch all up front errors that do not require server side thread to start
              if (result.status == 'AOB_ERROR') {
                ons.notification.toast(result.error, { timeout: 2000, animation: 'fall' })
                on_search_ended(result)
                return
              }
              get_aob_status();
            }
        });
    };



    //Private Methods
    function is_running(status) {
        return status == "AOB_SEARCH_RUNNING" || status == "AOB_CHECK_RUNNING";
    };

    function on_aob_upload_complete(result) {
        if (result.status == "AOB_ERROR") {
            ons.notification.toast(result.error, { timeout: 2000, animation: 'fall' })
            return
        }
        var name = result.name;
        configure_aobs(result.aob_list)
        var value = $(`#aob_search_names option[value='${name}']`).text();
        $('#aob_search_name').val(value);
        aob.aob_search_name_changed()
    };

    function on_search_started() {
        $("#aob_search_done_initial").hide()
        $("#aob_search_no_results").hide()
        $("#aob_search_done").hide()
        $("#aob_search_name").prop("disabled", true);
        $("#aob_search_names").prop("disabled", true);
        $("#aob_search_address").prop("disabled", true);
        $("#aob_search_value").prop("disabled", true);
        $("#aob_address_or_value").prop("disabled", true);
        $("#aob_search_size").prop("disabled", true);
        $("#aob_search_range").prop("disabled", true);
        $("#aob_upload_button").prop("disabled", true);
        hide_result_button()
        $("#aob_results_text").hide()
        $("#aob_run").prop("disabled",true);
    };

    function _download(filename, text) {
        var element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
   };

    function on_search_ended(result) {
        var can_continue = true
        var initial = false

        $("#aob_search_status").hide()
        $("#aob_run").prop("disabled", false);
        if (result.hasOwnProperty('aob_list')) {
          $('#aob_search_names').empty();
          if (result.aob_list.length > 0) {
            $('#aob_search_names').append($('<option>', { value: "_null", text: "" }));
            $("#aob_search_names").show()
          }
          $.each(result.aob_list , function (index, value) {
            $('#aob_search_names').append($('<option>', { value: value, text: value }));
          });
          $('#aob_search_names').val($("#aob_search_name").val())
        }
        if (!result.hasOwnProperty('possible_aobs')) {
            if (result.status != "AOB_SEARCH_IDLE" && result.status != "AOB_ERROR") {
                $("#aob_search_done_initial").show()
                initial = true
            }
        } else {
            $("#aob_search_done").show()
            $("#aob_count").text(result.possible_aobs)
            if (result.possible_aobs > 0) {
                check_results()
            } else {
                $("#aob_run").prop("disabled", true);
                can_continue = false
            }
        }

        $("#aob_search_name").prop("disabled", false);
        $("#aob_search_names").prop("disabled", false);
        $("#aob_search_address").prop("disabled", false);
        $("#aob_search_value").prop("disabled", false);
        $("#aob_address_or_value").prop("disabled", false);
        $("#aob_search_size").prop("disabled", false);
        $("#aob_search_range").prop("disabled", false);
        $("#aob_upload_button").prop("disabled", false);
        if (can_continue && !initial && result.status != "AOB_SEARCH_IDLE" && result.status != "AOB_ERROR") {
            $("#aob_view_results").show()
        }
        if (result.status == "AOB_SEARCH_IDLE" || result.status == "AOB_ERROR") {
            check_results()
        }

    }
    
    function hide_result_button() {
        $("#aob_search_done_initial").hide()
        $("#aob_search_no_results").hide()

        $("#aob_view_results").hide()
        $("#aob_view_results ons-switch")[0].checked = false
        $("#aob_results_text").hide();
    };

    function check_value_type() {
        if ( $("#aob_address_or_value").val() == "address") {
          $("#aob_search_type_address").show();
          $("#aob_search_type_value").hide();
        } else {
          $("#aob_search_type_value").show();
          $("#aob_search_type_address").hide();
        }
        check_run();
    };

    function configure_aobs(_aobs) {
        aob_list = _aobs;
        check_valid_aobs();

        $('#aob_search_names').empty();
        if (aob_list.length > 0) {
          $('#aob_search_names').append($('<option>', { value: "_null", text: "" }));
          $("#aob_search_names").show()
        }
        $.each(aob_list , function (index, value) {
          $('#aob_search_names').append($('<option>', { value: value, text: value }));
        });
    };

    function check_valid_aobs() {
        var name = $("#aob_search_name").val()
        if (aob_list.indexOf(name) == -1) {
          $("#aob_address_or_value option[value='address']").removeAttr('disabled');
          var sel = $("#aob_address_or_value").val();
          if (sel == 'value' || sel == null) {
            $("#aob_address_or_value").val('address')
            aob.aob_search_type_changed();
          }
          $("#aob_address_or_value option[value='value']").attr('disabled','disabled');
        } else {
          $("#aob_address_or_value option[value='value']").removeAttr('disabled');
        }
        if (aob_list.indexOf(name) == -1) {
            $("#aob_search_range_div").show();
        } else {
            $("#aob_search_range_div").hide();
        }
    };

    function show_results_button(count) {
        $("#aob_view_results span").text(count)
        if (count > 0) {
            $("#aob_view_results").show()
        }
    };

    function check_results() {
        var name = $("#aob_search_name").val()
        if (aob_list.indexOf(name) != -1) {
            $("#aob_run").prop("disabled", true);
            $("#aob_search_name").prop("disabled", true)
            $("#aob_search_names").prop("disabled", true)
            $.ajax
            ({
                url: '/aob',
                data: {"type": "AOB_GET_FILE", "name": name},
                type: 'post',
                success: function(result)
                {
                    $("#aob_search_name").prop("disabled", false)
                    $("#aob_search_names").prop("disabled", false)
                    $("#aob_search_done").hide()
                    $("#aob_address_or_value option[value='address']").attr('disabled','disabled');
                    $("#aob_address_or_value option[value='value']").attr('disabled','disabled');
                    if (result.address_search) { //an address search is possible
                        $("#aob_address_or_value option[value='address']").removeAttr('disabled');
                        $("#aob_address_or_value").val('address');
                    }
                    if (result.value_search) { //value search is possible
                        $("#aob_address_or_value option[value='value']").removeAttr('disabled','disabled');
                        $("#aob_address_or_value").val('value');
                    }
                    aob.aob_search_type_changed()
                    check_run();
                    show_results_button(result.count)
                    if (result.count == 0 && !result.value_search && !result.address_search) {
                        $("#aob_search_no_results").show()
                    }
                    $("#aob_results_text textarea").text(result.data)

                }
            });
        } else {
            hide_result_button()
        }
    };

    function check_run() {
        var type = $("#aob_address_or_value").val();
        if (type == 'address') {
            $("#aob_run").prop("disabled", current_process == "" || $("#aob_search_name").val() == "" || $("#aob_search_address").val() == "")
        } else {
            $("#aob_run").prop("disabled", current_process == "" || $("#aob_search_name").val() == "")
        }

        if ($("#aob_address_or_value option[value='value']").prop('disabled') && $("#aob_address_or_value option[value='address']").prop('disabled')) {
            $("#aob_run").prop("disabled", true)
        }
    };

    function get_aob_status() {
        $.ajax
        ({
            url: '/aob',
            data: {"type": "AOB_STATUS"},
            type: 'post',
            success: function(result)
            {
              if (result.status == 'AOB_ERROR') {
                ons.notification.toast(result.error, { timeout: 2000, animation: 'fall' })
                on_search_ended(result)
                return
              }
              current_process = result.process
              if (is_running(result.status)) {
                $("#aob_run").prop("disabled", true);
              }
              check_value_type();
              configure_aobs(result.aob_list);
              if (result.status != 'AOB_SEARCHING') {
                $("#aob_search_address").val(result.address == 0 ? '' : result.address);
                $("#aob_search_range").val(result.range == 0 ? 65536 : result.range);
                if ($("#aob_search_name").val() != result.name) {
                    $("#aob_search_name").val(result.name);
                    aob.aob_search_name_changed()
                }
              }
              if (result.process != "" && $("#aob_search_name").val() != "") {
                $("#aob_run").prop("disabled", false);
              }
              if (result.status == 'AOB_SEARCHING') {
                $("#aob_run").prop("disabled",true);
                if (result.hasOwnProperty('progress')) {
                    $("#aob_search_status").text(`Search currently in progress... ${result.progress}%`);
                } else {
                    $("#aob_search_status").text("Search currently in progress...");
                }
                $("#aob_search_status").show()
                $("#aob_run").prop("disabled",true);
                $("#aob_run_checker").prop("disabled",true);
                setTimeout(get_aob_status, 1000);
              }
              else {
                on_search_ended(result)
              }
            }
        });
    }



}( window.aob = window.aob || {}, jQuery ));







