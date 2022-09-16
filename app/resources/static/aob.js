(function( aob, $, undefined ) {
    //Private Property
    var div_aob_information_block;
    var inp_aob_name;
    var sel_aob_name;
    var sel_aob_search_type;
    var heading_address_value;
    var inp_address_value;
    var sel_value_size;
    var row_aob_range;
    var inp_aob_range;
    var btn_search;
    var div_search_results;
    var row_search_progress;
    var search_progress;
    var row_aob_initial_search;
    var row_search_results_header;
    var row_search_result_count;
    var result_count;
    var btn_download;

    var aob_list = [];
    var current_process = "";
    var current_state = "AOB_STATE_START";
    var current_search_type = "address";
    var valid_search_types = ['address']
    var current_address = ""
    var current_value = ""
    var current_progress = 0
    var is_initial_search = false
    var search_results = []
    var search_result_count = 0
    var result_refresh = false
    var is_final_search = false
    var current_name = ""
    var current_select = ""

    var row_item_template = '<ons-row class="result_row" id="result_##count##"><ons-col align="center" width="75px" class="col ons-col-inner aob_size" id="result_size_##count##">##size##</ons-col><ons-col align="center" width="100px" class="col ons-col-inner aob_offset" id="result_offset_##count##">##offset##</ons-col> <ons-col align="center" width="50%" class="col ons-col-inner aob" id="result_aob_##count##">##aob##</ons-col></ons-row>'

    //Public Property
    aob.test = "Bacon Strips";

    //Public Method
    aob.ready = function() {
        div_aob_information_block = $("#aob_information_block");
        inp_aob_name = $("#aob_name");
        sel_aob_name = $("#aob_selection");
        sel_aob_search_type = $("#aob_search_type");
        heading_address_value = $("#aob_address_value_heading");
        inp_address_value = $("#aob_address_value");
        sel_value_size = $("#aob_value_size");
        row_aob_range = $("#aob_range_row");
        inp_aob_range = $("#aob_range");
        btn_search = $("#aob_search_button");
        div_search_results = $("#aob_search_results");
        row_search_progress = $("#aob_search_progress_row");
        row_aob_initial_search = $("#aob_initial_search_row");
        search_progress = $("#aob_search_progress");
        row_search_results_header = $("#aob_search_results_header");
        row_search_result_count = $("#aob_search_result_count_row");
        result_count = $("#aob_result_count");
        btn_download = $("#aob_download_button");

        disable([btn_search])
        $.send('/aob', { "command": "AOB_INITIALIZE" }, on_aob_status);


    };

    aob.aob_search_type_changed = function(element) {
        current_search_type = sel_aob_search_type.children('option:selected').val()
        on_aob_status()
    };

    aob.on_process_changed = function(process) {
        if (process !== current_process) {
            current_process = process
            on_process_changed(process)
        }
    };

    aob.on_info_process = function(process) {
        current_process = process
    }

    aob.aob_address_value_changed = function(element) {
        var v = inp_address_value.val()
        if (current_search_type === 'address') {
            current_address = v
        } else {
            current_value = v
        }
        on_aob_status()
    }

    aob.aob_search_name_selected = function(element) {
        var value = sel_aob_name.children('option:selected').text();
        inp_aob_name.val(value)
        aob.aob_search_name_changed(element)
    };

    aob.aob_search_name_changed = function(element) {
        on_search_name_changed()
    };

    aob.aob_search_clicked = function(element) {
        var name = inp_aob_name.val()
        var search_type = sel_aob_search_type.val()
        var range = inp_aob_range.val()
        var address_value = inp_address_value.val()
        var value_size = sel_value_size.val()
        disable([btn_search])
        current_progress = 0
        $.send('/aob', { "command": "AOB_SEARCH", "name": name, "search_type": search_type, "range": range, "address_value": address_value, "value_size": value_size }, on_aob_status);
    };

    aob.on_download_clicked = function(element) {
        disable([btn_download])
        var name = inp_aob_name.val()
        /*$.get( "/aob", { name: name }, function(res){
            console.log(res)
        } );*/
        $.ajax({
            type: "GET",
            url: '/aob',
            data: { "name": name },
            xhrFields: {
                responseType: 'blob' // to avoid binary data being mangled on charset conversion
            },
            success: function(blob, status, xhr) {
                // check for a filename
                var filename = "";
                var disposition = xhr.getResponseHeader('Content-Disposition');
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    var matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) filename = matches[1].replace(/['"]/g, '');
                }

                if (typeof window.navigator.msSaveBlob !== 'undefined') {
                    // IE workaround for "HTML7007: One or more blob URLs were revoked by closing the blob for which they were created. These URLs will no longer resolve as the data backing the URL has been freed."
                    window.navigator.msSaveBlob(blob, filename);
                } else {
                    var URL = window.URL || window.webkitURL;
                    var downloadUrl = URL.createObjectURL(blob);

                    if (filename) {
                        // use HTML5 a[download] attribute to specify filename
                        var a = document.createElement("a");
                        // safari doesn't support this yet
                        if (typeof a.download === 'undefined') {
                            window.location.href = downloadUrl;
                        } else {
                            a.href = downloadUrl;
                            a.download = filename;
                            document.body.appendChild(a);
                            a.click();
                        }
                    } else {
                        window.location.href = downloadUrl;
                    }

                    setTimeout(function () { URL.revokeObjectURL(downloadUrl); on_aob_status() }, 100); // cleanup
                }
            }
        });
    }

    aob.aob_upload_file_changed = function(file) {
        if (file.size > 600000) {
            ons.notification.toast('File must be under 600KB', { timeout: 2000, animation: 'fall' })
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
            $.post('/aob', { "command": "AOB_UPLOAD", data: result, name: fileName }, on_aob_status);
        }
    }

    //Private Methods
    function show(elements, _show=true) {
        $.each(elements, function(index, element){
            if (_show) {
                element.show();
            } else {
                element.hide();
            }
        });
    }

    function hide(elements) {
        show(elements, false);
    }

    function enable(elements, _enable=true) {
        $.each(elements, function(index, element){
            if (_enable) {
                element.removeAttr('disabled');
            } else {
                element.attr('disabled', 'disabled')
            }
        });
    }

    function disable(elements) {
        enable(elements, false);
    }

    function on_aob_status(result={}) {
        current_state = result.state || current_state
        current_search_type = result.search_type || current_search_type
        valid_search_types = result.valid_searches || valid_search_types
        aob_list = result.names || aob_list
        current_progress = result.progress || current_progress
        //current_search_round = result.search_round || current_search_round
        aob_list = result.aob_list || aob_list
        is_initial_search = result.hasOwnProperty('initial_search') ? result.initial_search : is_initial_search
        is_final_search = result.hasOwnProperty('is_final') ? result.is_final : is_final_search
        search_results = result.search_results || search_results
        search_result_count =  result.hasOwnProperty('number_of_results') ? result.number_of_results : search_result_count
        result_refresh = result.hasOwnProperty('number_of_results')
        current_name = result.hasOwnProperty('name') ? result.name : ""
        current_select = result.hasOwnProperty('select') ? result.select : ""
        var repeat = result.repeat || 0
        var error = result.error || ""
        var message = result.message || ""
        switch (current_state) {
            case 'AOB_STATE_START':
                setup_start_state()
                populate_names()
                break;
            case 'AOB_STATE_SEARCHING':
                setup_searching_state()
                break;
            case 'AOB_STATE_CONTINUE':
                setup_continue_state()
                populate_names()
                break;
        }
        if (repeat > 0) {
            setTimeout(function() {$.send('/aob', { "command": "AOB_STATUS" }, on_aob_status);}, repeat)
        }
        if (error.length > 0) {
            ons.notification.toast(error, { timeout: 5000, animation: 'fall' })
        }
        if (message.length > 0) {
            ons.notification.toast(message, { timeout: 2000, animation: 'fall' })
        }

    }

    function on_search_name_changed() {
        var selection = sel_aob_name.children('option:selected').text();
        var value = inp_aob_name.val()
        if (aob_list.indexOf(value) > -1) {
            sel_aob_name.children(`option[value="${value}"]`).prop('selected', true)
            on_name_selected(value)
        } else {
            sel_aob_name.children(`option[value="_null"]`).prop('selected', true)
            valid_search_types = ['address']
            is_final_search = false
            current_search_type = 'address'
            current_state = 'AOB_STATE_START'
            on_aob_status()
        }
    }

    function setup_state_info(shows, hides) {
        if (current_process === "" || current_state == 'AOB_STATE_SEARCHING') {
            disable([btn_search, inp_aob_name, sel_aob_name, sel_aob_search_type, inp_address_value, inp_aob_range]);
            return
        }
        enable([btn_search, inp_aob_name, sel_aob_name, sel_aob_search_type, inp_address_value, inp_aob_range]);
        if (inp_aob_name.val() === "") {
            disable([btn_search, sel_aob_search_type, inp_address_value, inp_aob_range]);
        }
        else {
            if (aob_list.indexOf(inp_aob_name.val()) > -1) {
                hides.push(row_aob_range)
            } else {
                shows.push(row_aob_range)
                if (inp_aob_range.val() === '' || isNaN(filterInt(inp_aob_range.val()))) {
                    inp_aob_range.val(65536)
                }
            }
            if (current_search_type === 'address') {
                if (current_address === '' || isNaN(parseInt(current_address, 16))) {
                    disable([btn_search])
                } else if (parseInt(current_address, 16) < 4095) {
                    disable([btn_search])
                } else {
                    enable([btn_search])
                }
            } else {
                enable([btn_search])
            }
            if (is_final_search) {
                disable([btn_search])
            }
        }
    }

    function setup_start_state() {
        var shows = [div_aob_information_block]
        var hides = [div_search_results]
        setup_search_type(shows, hides)
        setup_state_info(shows, hides)
        show(shows)
        hide(hides)

    }

    function setup_search_type(_shows, _hides) {
        sel_aob_search_type.val(current_search_type)
        if (current_search_type === 'address') {
            heading_address_value.text('Address:')
            _shows.push(row_aob_range)
            _hides.push(sel_value_size)
            inp_address_value.val(current_address)
        } else {
            heading_address_value.text('Value:')
            _hides.push(row_aob_range)
            _shows.push(sel_value_size)
            inp_address_value.val(current_value)
        }
        sel_aob_search_type.children().each(function(index, item){
            $(item).prop('disabled', true)
        })
        $.each(valid_search_types, function(index, item) {
            sel_aob_search_type.children(`option[value="${item}"]`).removeAttr('disabled')
        })
    }

    function setup_searching_state() {
        var shows = [div_aob_information_block, row_search_progress, div_search_results]
        var hides = [row_search_results_header, row_search_result_count, btn_download, row_aob_initial_search, $(".result_row"), row_aob_range]
        setup_search_type(shows, hides)
        show(shows)
        hide(hides)
        disable([btn_search, inp_aob_name, sel_aob_name, sel_aob_search_type, inp_address_value, inp_aob_range]);
        search_progress.text(current_progress+'%')
    }

    function setup_continue_state() {
        var shows = [div_aob_information_block, div_search_results, row_search_results_header, btn_download]
        var hides = [row_search_progress]
        var enables = [inp_aob_name, sel_aob_name, sel_aob_search_type, inp_address_value, inp_aob_range, btn_download]
        var disables = []
        var last_search = ""
        //if (current_search_type == 'address' )
        if (is_initial_search) {
            shows.push(row_aob_initial_search)
            hides.push(...[row_search_results_header, row_search_result_count, row_aob_range])
        } else {
            hides.push(...[row_aob_initial_search,row_aob_range])
            shows.push(...[row_search_results_header, row_search_result_count])
            if (result_refresh) {
                result_count.text(search_result_count)
                div_search_results.children('.result_row').remove()
                for (i=0; i<search_results.length; i++) {
                    var result = search_results[i]
                    var size = search_results[i].size
                    var offset = search_results[i].offset
                    var aob = search_results[i].aob
                    var ele_txt = row_item_template.replaceAll('##count##', i).replaceAll('##size##', size).replaceAll('##offset##', offset).replaceAll('##aob##', aob)
                    div_search_results.append(ele_txt)
                }
                result_refresh = false
            }
        }
        setup_search_type(shows, hides)
        enable(enables);
        disable(disables)
        setup_state_info(shows, hides)
        if (current_select != "") {
            sel_aob_name.children(`option[value="${current_select}"]`).prop('selected', true)
        }
        if (current_name != "") {
            inp_aob_name.val(current_name)
            on_search_name_changed()
        }
        show(shows);
        hide(hides);
    }

    function on_process_changed(process) {
        $.send('/aob', { "command": "AOB_RESET", "process": process }, on_aob_status);
    }

    function populate_names() {
        var current_options = []
        sel_aob_name.children("option").each(function(index, item) {
            current_options.push(item.value)
        })
        $.each(aob_list , function (index, value) {
          if (current_options.indexOf(value) == -1) {
            sel_aob_name.append($('<option>', { value: value, text: value, selected: inp_aob_name.val() == value }));
          }
        });
        if (aob_list.indexOf(inp_aob_name.val()) > -1 && inp_aob_name.val() !== sel_aob_name.children("option:selected").text()) {
            sel_aob_name.children(`option [value="${inp_aob_name.val()}"]`).prop('selected', true)
        }
    }

    function on_name_selected(name) {
        inp_aob_name.blur()
        disable([inp_aob_name, sel_aob_name])
        $.send('/aob', { "command": "AOB_SELECT", "name": name }, on_aob_status);
    }

    function filterInt(value) {
        return /^[-+]?(\d+)$/.test(value) ? Number(value) : NaN;
    }
}( window.aob = window.aob || {}, jQuery ));







