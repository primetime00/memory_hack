(function( aob, $, undefined ) {
    //Private Property
    var flow_map = {"FLOW_START": 0, "FLOW_SEARCHING": 1, "FLOW_RESULTS": 2, "FLOW_NO_RESULTS": 3, "FLOW_LOOKUP": 4, "FLOW_WORKING": 5, "FLOW_INITIAL_COMPLETE": 6}
    var current_flow = flow_map["FLOW_START"]
    var value_valid = false
    var range_valid = false

    var sel_aob_process;
    var div_aob_block;
    var div_aob_information_block;
    var inp_aob_name;
    var sel_aob_name;
    var sel_aob_search_type;
    var heading_address_value;
    var inp_address_value;
    var sel_value_size;
    var txt_value_address;
    var row_aob_range;
    var inp_aob_range;
    var btn_search;
    var switch_repeat;
    var div_search_results;
    var row_search_progress;
    var search_progress;
    var row_aob_initial_search;
    var div_search_result_container;
    var row_search_result_count;
    var result_count;
    var btn_download;
    var btn_delete_file;

    var aob_list = [];
    var result_list = [];

    var row_item_template = [
        '<ons-list-item class="result_row" id="result_##count##" style="margin-bottom:10px;">',
            '<ons-row>',
                '<ons-col name="offset" align="center" width="25%" class="col ons-col-inner aob_offset" id="result_offset_##count##" data-offset="##offset##">##offset##</ons-col>',
                '<ons-col name="size" align="center" width="12%" class="col ons-col-inner aob_size" id="result_size_##count##">##size##</ons-col>',
                '<ons-col align="center" width="20%" class="col ons-col-inner"><ons-button modifier="quiet" name="count_button" onclick="aob.count_result(##count##, this)">Count</ons-button></ons-col>',
                '<ons-col  name="counts" align="center" width="12%" class="col ons-col-inner" id="aob_counts_##count##"></ons-col>',
                '<ons-col align="center" width="13%" class="col ons-col-inner aob"><ons-button modifier="quiet" name="delete_button" onclick="aob.delete_result(##count##, this)"><ons-icon icon="md-delete" size="20px"/></ons-button></ons-col>',
                '<ons-col align="center" width="13%" class="col ons-col-inner aob" id="result_aob_##count##"><ons-button modifier="quiet" name="copy_button" onclick="aob.copy_result(##count##, this)" ##disabled##><ons-icon icon="md-copy" size="20px"/></ons-button></ons-col>',
            '</ons-row>',
            '<ons-row>',
                '<ons-col  name="aob" align="center" width="95%" class="col ons-col-inner aob" id="result_aob_##count##">##aob##</ons-col>',
            '</ons-row>',
        '</ons-list-item>'].join('\n')

    //Public Property
    aob.test = "Bacon Strips";

    //Public Method
    aob.ready = function() {
        sel_aob_process = $("#aob_process")
        div_aob_block = $("#aob_block")
        div_aob_information_block = $("#aob_information_block");
        inp_aob_name = $("#aob_name");
        sel_aob_name = $("#aob_selection");
        sel_aob_search_type = $("#aob_search_type");
        heading_address_value = $("#aob_address_value_heading");
        inp_address_value = $("#aob_address_value");
        sel_value_size = $("#aob_value_size");
        txt_value_address = $("#val_address_text");
        row_aob_range = $("#aob_range_row");
        inp_aob_range = $("#aob_range");
        btn_search = $("#aob_search_button");
        switch_repeat = $("#aob_repeat_switch");
        div_search_results = $("#aob_search_results");
        row_search_progress = $("#aob_search_progress_row");
        row_aob_initial_search = $("#aob_initial_search_row");
        search_progress = $("#aob_search_progress");
        $("#aob_paste_button").hide()

        div_search_result_container = $("#aob_result_container");
        row_search_result_count = $("#aob_search_result_count_row");
        result_count = $("#aob_result_count");
        btn_download = $("#aob_download_button");
        btn_delete_file = $("#aob_delete_file_button");
    };

    aob.on_update_process_list = function(process_list_add, process_list_remove) {
        var options = sel_aob_process.children('option');
        var selected = sel_aob_process.find('option:selected')
        if (process_list_remove.includes(selected.val())) {
            div_aob_block.hide()
        }
        for (var i=options.length-1; i>=0; i--) {
            var option=options[i]
            if (process_list_remove.includes(option.value)) {
                option.remove()
            }
        }
        var f = sel_aob_process.find('option:first')
        for (const item of process_list_add) {
            f.after($('<option>', {value: item, text: item}))
            f = sel_aob_process.find('option:last')
        }
    }

    aob.on_update_selected_process = function(process_name) {
        var value = sel_aob_process.val()
        if (value != process_name){
            set_process(process_name)
        }
    }

    aob.on_process_changed = function(process) {
        process_control.request_process(process, 'aob', function(result){
            if (!result.success) {
                set_process('_null')
                ons.notification.toast(result.error, { timeout: 4000, animation: 'fall' })
            } else {
                set_process(process)
            }
        })
    };

    aob.aob_search_type_changed = function(value) {
        update(sel_aob_search_type)
    };

    aob.aob_address_value_changed = function(value) {
        update(inp_address_value)
    }

    aob.aob_search_name_selected = function(value) {
        update(sel_aob_name)
    };

    aob.aob_search_name_changed = function(value) {
        update(inp_aob_name)
    };

    aob.aob_size_changed = function(value) {
        update(sel_value_size)
    }

    aob.aob_range_changed = function(value) {
        update(inp_aob_range)
    }

    aob.aob_search_clicked = function(element) {
        var name_input = inp_aob_name.val()
        var name_select = sel_aob_name.val()
        var search_type = sel_aob_search_type.val()
        var value = inp_address_value.val()
        var size = sel_value_size.val()
        var range = inp_aob_range.val()
        var repeat = switch_repeat.prop('checked')

        if (current_flow == flow_map['FLOW_WORKING']) { //we are requesting a stop!
            $.send('/aob', { "command": "AOB_RESET", "name": name_input, "search_type": search_type, "range": range, "address_value": value, "value_size": size }, on_aob_status);
        } else {
            current_flow = flow_map['FLOW_WORKING']
            $.send('/aob', { "command": "AOB_SEARCH", "name": name_input, "search_type": search_type, "range": range, "address_value": value, "value_size": size, "repeat": repeat }, on_aob_status);
            update(btn_search)
        }
    };

    aob.on_delete_file_clicked = function(element) {
        ons.createElement('delete_aob_file', { append: true }).then(function(dialog) {
            var name = sel_aob_name.val()
            $(dialog).find('#delete_aob_file_name').text(name)
            $(dialog).find('ons-alert-dialog-button[name="cancel_button"]').bind('click', () => {dialog.hide()})
            $(dialog).find('ons-alert-dialog-button[name="delete_button"]').bind('click', () => {
                $.send('/aob', { 'command': "AOB_DELETE_FILE", 'file': name}, on_aob_status);
                dialog.hide()
            })
            dialog.show();
        });
    }

    aob.on_download_clicked = function(element) {
        btn_download.attr('disabled', 'disabled')
        var name = inp_aob_name.val()
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

                    setTimeout(function () { URL.revokeObjectURL(downloadUrl); btn_download.removeAttr('disabled') }, 100); // cleanup
                }
            }
        });
    }

    aob.aob_upload_file_changed = function(file) {
        $('#aob_upload_button').val("");
        if (file.size > 60000000) {
            ons.notification.toast('File must be under 60MB', { timeout: 2000, animation: 'fall' })
            return
        } else if (file.size <= 20) {
            ons.notification.toast('AOB file is too small.', { timeout: 2000, animation: 'fall' })
            return
        }
        var reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = function(event) {
            var result = event.target.result;
            var fileName = file.name;
            $.post('/aob', { "command": "AOB_UPLOAD", data: result, name: fileName }, on_aob_status);
        }
    }

    aob.count_result = function(index, element) {
        $.post('/aob', { "command": "AOB_COUNT", index: index, name: inp_aob_name.val() }, on_aob_status);
    }

    aob.delete_result = function(index, element) {
        $.post('/aob', { "command": "AOB_DELETE", index: index, name: inp_aob_name.val() }, on_aob_status);
    }


    aob.copy_result = function(index, element) {
        var offset = result_list[index].offset.startsWith('-') ? result_list[index].offset.replace('-', '') : '-'+result_list[index].offset
        document.clipboard.copy({'aob': result_list[index].aob, 'offset': offset})
    }

    aob.clipboard_data_copied = function(data) {
        if (has(data, 'address') || has(data, 'value')) {
            $("#aob_paste_button").show()
        }
    }

    aob.clipboard_data_pasted = function(data, desc) {
        if (sel_aob_search_type.val() === 'value') {
            if (has(data, 'value')) {
                inp_address_value.val(data.value.Display)
            } else {
                if (has(data, 'address')) {
                    sel_aob_search_type.val('address')
                    update(sel_aob_search_type)
                    if (has(data, 'resolved')) {
                        inp_address_value.val(data.resolved)
                    } else {
                        inp_address_value.val(data.address)
                    }
                }
            }
            update(inp_address_value)
        } else {
            if (has(data, 'address')) {
                if (has(data, 'resolved')) {
                    inp_address_value.val(data.resolved)
                } else {
                    inp_address_value.val(data.address)
                }
            } else if (sel_aob_search_type.find('option[value="value"]').length > 0) {
                if (has(data, 'value')) {
                    sel_aob_search_type.val('value')
                    update(sel_aob_search_type)
                    inp_address_value.val(data.value.Display)
                }
            }
            update(inp_address_value)
        }
    }

    aob.clipboard_data_cleared = function() {
        $("#aob_paste_button").hide()
    }

    aob.on_tab_set = function(tab) {
    };


    //Private Methods
    function on_aob_ready() {
        $.send('/aob', { "command": "AOB_INITIALIZE" }, on_aob_status);
    }

    function set_process(process_name) {
        sel_aob_process.val(process_name)
        if (process_name === '_null') {
            process_name = ''
        }
        if (process_name.length > 0) {
            div_aob_block.show()
            on_aob_ready()
        } else {
            div_aob_block.hide()
        }
    }

    function on_aob_status(result) {
        current_flow = has(result, 'flow') ? result.flow : current_flow
        var repeat = has(result, 'flow') ? result.repeat : 0
        result.has_error = has(result, 'error') && result.error !== ""
        result.error = result.error || ""
        setup_aob_name(result)
        setup_aob_name_list(result)
        setup_aob_type(result)
        setup_aob_value(result)
        setup_aob_size(result)
        setup_aob_range(result)
        setup_aob_search_button(result)
        setup_aob_progress(result)
        setup_aob_results(result)
        //setup_reset_button(result)
        //setup_results_progress(result)
        //setup_results_list(result)
        if (result.error !== "") {
            ons.notification.toast(result.error, { timeout: 5000, animation: 'fall' })
        }
        if (has(result, 'message')) {
            ons.notification.toast(result.message, { timeout: 3000, animation: 'fall' })
        }
        if (repeat > 0) {
            setTimeout(function(){
                $.send('/aob', { "command": "AOB_STATUS" }, on_aob_status);
            }, repeat);
        }
    }

    function setup_aob_name(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                inp_aob_name.removeAttr('disabled')
                if (has(result, 'name')) {
                    inp_aob_name.val(result.name)
                } else {
                    inp_aob_name.val("")
                }
                break
            case flow_map["FLOW_WORKING"]:
                inp_aob_name.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                inp_aob_name.removeAttr('disabled')
                if (has(result, 'name')) {
                    inp_aob_name.val(result.name)
                } else {
                    inp_aob_name.val("")
                }
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                inp_aob_name.removeAttr('disabled')
                if (has(result, 'name')) {
                    inp_aob_name.val(result.name)
                } else {
                    inp_aob_name.val("")
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                inp_aob_name.removeAttr('disabled')
                if (has(result, 'name')) {
                    inp_aob_name.val(result.name)
                } else {
                    inp_aob_name.val("")
                }
                break
        }
    }

    function setup_aob_name_list(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                btn_delete_file.hide()
                sel_aob_name.removeAttr('disabled')
                if (has(result, 'names')) {
                    sel_aob_name.find('option[value != "_null"]').remove()
                    result.names.forEach((item, index) => {
                        sel_aob_name.find('option:first').after($('<option>', {value: item, text: item}))
                    })
                    aob_list = result.names
                }
                if (inp_aob_name.val() === "") {
                    sel_aob_name.val("_null")
                } else if (result.names.includes(inp_aob_name.val())) {
                    sel_aob_name.val(inp_aob_name.val())
                }
                break
            case flow_map["FLOW_WORKING"]:
            btn_delete_file.hide()
                sel_aob_name.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                sel_aob_name.removeAttr('disabled')
                if (has(result, 'names')) {
                    sel_aob_name.find('option[value != "_null"]').remove()
                    result.names.forEach((item, index) => {
                        sel_aob_name.find('option:first').after($('<option>', {value: item, text: item}))
                    })
                    aob_list = result.names
                }
                if (inp_aob_name.val() === "") {
                    sel_aob_name.val("_null")
                } else if (result.names.includes(inp_aob_name.val())) {
                    sel_aob_name.val(inp_aob_name.val())
                }
                btn_delete_file.show()
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                sel_aob_name.removeAttr('disabled')
                if (has(result, 'names')) {
                    sel_aob_name.find('option[value != "_null"]').remove()
                    result.names.forEach((item, index) => {
                        sel_aob_name.find('option:first').after($('<option>', {value: item, text: item}))
                    })
                    aob_list = result.names
                }
                if (inp_aob_name.val() === "") {
                    sel_aob_name.val("_null")
                } else if (result.names.includes(inp_aob_name.val())) {
                    sel_aob_name.val(inp_aob_name.val())
                }
                btn_delete_file.show()
                break
            case flow_map["FLOW_NO_RESULTS"]:
                sel_aob_name.removeAttr('disabled')
                if (has(result, 'names')) {
                    sel_aob_name.find('option[value != "_null"]').remove()
                    result.names.forEach((item, index) => {
                        sel_aob_name.find('option:first').after($('<option>', {value: item, text: item}))
                    })
                    aob_list = result.names
                }
                if (inp_aob_name.val() === "") {
                    sel_aob_name.val("_null")
                } else if (result.names.includes(inp_aob_name.val())) {
                    sel_aob_name.val(inp_aob_name.val())
                }
                btn_delete_file.show()
                break
        }
    }

    function setup_aob_type(result){
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                sel_aob_search_type.removeAttr('disabled')
                if (has(result, 'valid_types')) {
                    sel_aob_search_type.find('option').hide()
                    result.valid_types.forEach((item, index) => {
                        sel_aob_search_type.find(`option[value=${item}]`).show()
                    })
                }
                if (has(result, 'type')) {
                    sel_aob_search_type.val(result.type)
                } else {
                    sel_aob_search_type.prop("selectedIndex", 0);
                }
                if (sel_aob_search_type.val() === 'address') {
                    txt_value_address.text("Address")
                } else {
                    txt_value_address.text("Value")
                }
                break
            case flow_map["FLOW_WORKING"]:
                sel_aob_search_type.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                sel_aob_search_type.removeAttr('disabled')
                if (has(result, 'valid_types')) {
                    sel_aob_search_type.find('option').hide()
                    result.valid_types.forEach((item, index) => {
                        sel_aob_search_type.find(`option[value=${item}]`).show()
                    })
                }
                if (has(result, 'type')) {
                    sel_aob_search_type.val(result.type)
                } else {
                    sel_aob_search_type.prop("selectedIndex", 0);
                }
                if (sel_aob_search_type.val() === 'address') {
                    txt_value_address.text("Address")
                } else {
                    txt_value_address.text("Value")
                }
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                sel_aob_search_type.removeAttr('disabled')
                if (has(result, 'valid_types')) {
                    sel_aob_search_type.find('option').hide()
                    result.valid_types.forEach((item, index) => {
                        sel_aob_search_type.find(`option[value=${item}]`).show()
                    })
                }
                if (has(result, 'type')) {
                    sel_aob_search_type.val(result.type)
                } else {
                    sel_aob_search_type.prop("selectedIndex", 0);
                }
                if (sel_aob_search_type.val() === 'address') {
                    txt_value_address.text("Address")
                } else {
                    txt_value_address.text("Value")
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                sel_aob_search_type.removeAttr('disabled')
                if (has(result, 'valid_types')) {
                    sel_aob_search_type.find('option').hide()
                    result.valid_types.forEach((item, index) => {
                        sel_aob_search_type.find(`option[value=${item}]`).show()
                    })
                }
                if (has(result, 'type')) {
                    sel_aob_search_type.val(result.type)
                } else {
                    sel_aob_search_type.prop("selectedIndex", 0);
                }
                if (sel_aob_search_type.val() === 'address') {
                    txt_value_address.text("Address")
                } else {
                    txt_value_address.text("Value")
                }
                break
        }
    }

    function setup_aob_value(result){
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                inp_address_value.removeAttr('disabled')
                if (has(result, 'value')) {
                    inp_address_value.val(result.value)
                }
                validate_value(inp_address_value.val(), sel_value_size.val(), sel_aob_search_type.val())
                break
            case flow_map["FLOW_WORKING"]:
                inp_address_value.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                inp_address_value.removeAttr('disabled')
                if (has(result, 'value')) {
                    inp_address_value.val(result.value)
                }
                validate_value(inp_address_value.val(), sel_value_size.val(), sel_aob_search_type.val())
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                inp_address_value.removeAttr('disabled')
                if (has(result, 'value')) {
                    inp_address_value.val(result.value)
                }
                validate_value(inp_address_value.val(), sel_value_size.val(), sel_aob_search_type.val())
                break
            case flow_map["FLOW_NO_RESULTS"]:
                inp_address_value.removeAttr('disabled')
                if (has(result, 'value')) {
                    inp_address_value.val(result.value)
                }
                validate_value(inp_address_value.val(), sel_value_size.val(), sel_aob_search_type.val())
                break
        }
    }

    function setup_aob_size(result){
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                sel_value_size.removeAttr('disabled')
                var sz = sel_value_size.find('option:selected').val()
                if (has(result, 'size')) {
                    sz = result.size
                }
                if (sel_aob_search_type.val() === 'address') {
                    sel_value_size.hide()
                } else {
                    sel_value_size.show()
                    sel_value_size.val(result.size)
                }
                break
            case flow_map["FLOW_WORKING"]:
                sel_value_size.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                sel_value_size.removeAttr('disabled')
                var sz = sel_value_size.find('option:selected').val()
                if (has(result, 'size')) {
                    sz = result.size
                }
                if (sel_aob_search_type.val() === 'address') {
                    sel_value_size.hide()
                } else {
                    sel_value_size.show()
                    sel_value_size.val(result.size)
                }
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                sel_value_size.removeAttr('disabled')
                var sz = sel_value_size.find('option:selected').val()
                if (has(result, 'size')) {
                    sz = result.size
                }
                if (sel_aob_search_type.val() === 'address') {
                    sel_value_size.hide()
                } else {
                    sel_value_size.show()
                    sel_value_size.val(result.size)
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                sel_value_size.removeAttr('disabled')
                var sz = sel_value_size.find('option:selected').val()
                if (has(result, 'size')) {
                    sz = result.size
                }
                if (sel_aob_search_type.val() === 'address') {
                    sel_value_size.hide()
                } else {
                    sel_value_size.show()
                    sel_value_size.val(result.size)
                }
                break
        }
    }

    function setup_aob_range(result){
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                inp_aob_range.removeAttr('disabled')
                if (has(result, 'range')) {
                    inp_aob_range.val(result.range)
                }
                validate_range(inp_aob_range.val())
                row_aob_range.show()
                break
            case flow_map["FLOW_WORKING"]:
                inp_aob_range.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                inp_aob_range.removeAttr('disabled')
                row_aob_range.hide()
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                inp_aob_range.removeAttr('disabled')
                row_aob_range.hide()
                break
            case flow_map["FLOW_NO_RESULTS"]:
                inp_aob_range.removeAttr('disabled')
                if (has(result, 'range')) {
                    inp_aob_range.val(result.range)
                }
                validate_range(inp_aob_range.val())
                row_aob_range.show()
                break
        }
    }

    function setup_aob_search_button(result){
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                btn_search.text('Search')
                if (value_valid && range_valid && inp_aob_name.val().length > 0) {
                    btn_search.removeAttr('disabled')
                    if (sel_aob_search_type.val() === 'address') {
                        switch_repeat.removeAttr('disabled')
                    } else {
                        switch_repeat.prop('checked', false)
                        switch_repeat.attr('disabled', 'disabled')
                    }
                } else {
                    btn_search.attr('disabled', 'disabled')
                    switch_repeat.attr('disabled', 'disabled')
                }
                break
            case flow_map["FLOW_WORKING"]:
                btn_search.text('Stop')
                btn_search.removeAttr('disabled')
                switch_repeat.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                btn_search.text('Search')
                if (value_valid && range_valid && inp_aob_name.val().length > 0) {
                    btn_search.removeAttr('disabled')
                    if (sel_aob_search_type.val() === 'address') {
                        switch_repeat.removeAttr('disabled')
                    } else {
                        switch_repeat.prop('checked', false)
                        switch_repeat.attr('disabled', 'disabled')
                    }
                } else {
                    btn_search.attr('disabled', 'disabled')
                    switch_repeat.attr('disabled', 'disabled')
                }
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                if (switch_repeat.prop('checked')) {
                    btn_search.text('Stop')
                } else {
                    btn_search.text('Search')
                }
                if (value_valid && range_valid && inp_aob_name.val().length > 0) {
                    btn_search.removeAttr('disabled')
                    if (sel_aob_search_type.val() === 'address') {
                        switch_repeat.removeAttr('disabled')
                    } else {
                        switch_repeat.prop('checked', false)
                        switch_repeat.attr('disabled', 'disabled')
                    }
                } else {
                    btn_search.attr('disabled', 'disabled')
                    switch_repeat.attr('disabled', 'disabled')
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                btn_search.text('Search')
                btn_search.attr('disabled', 'disabled')
                switch_repeat.attr('disabled', 'disabled')
                break
        }
    }

    function setup_aob_progress(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                div_search_results.hide()
                row_search_progress.hide()
                row_aob_initial_search.hide()
                break
            case flow_map["FLOW_WORKING"]:
                div_search_results.show()
                row_search_progress.show()
                row_aob_initial_search.hide()
                search_progress.text(result.progress)
                break
            case flow_map["FLOW_RESULTS"]:
                div_search_results.show()
                row_aob_initial_search.hide()
                row_search_progress.hide()
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                div_search_results.show()
                row_aob_initial_search.hide()
                row_search_progress.hide()
                break
            case flow_map["FLOW_NO_RESULTS"]:
                div_search_results.show()
                row_aob_initial_search.hide()
                row_search_progress.hide()
                break
        }
    }

    function setup_aob_results(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                row_aob_initial_search.hide()
                div_search_results.hide()
                div_search_result_container.hide()
                row_search_result_count.hide()
                btn_download.hide()
                div_search_results.children('.result_row').hide()
                break
            case flow_map["FLOW_WORKING"]:
                row_aob_initial_search.hide()
                div_search_result_container.hide()
                row_search_result_count.hide()
                btn_download.hide()
                div_search_results.children('.result_row').hide()
                break
            case flow_map["FLOW_RESULTS"]:
                row_aob_initial_search.hide()
                if (has(result, 'results')){
                    result_list = result.results
                    result_count.text(result.results.length)
                    var last_index = 0
                    for (i=0; i<result.results.length; i++) {
                        var rz = result.results[i]
                        var aob_count = ''
                        if (has(rz, 'count')) {aob_count = rz.count.toString() }
                        var size = rz.size
                        var offset = rz.offset
                        var aob = rz.aob
                        var res_id = $("#result_"+i)
                        last_index = i+1
                        if (res_id.length > 0) {
                            res_id.find('[name="offset"]').html(offset)
                            res_id.find('[name="size"]').html(size)
                            res_id.find('[name="counts"]').html('<b>'+aob_count+'</b>')
                            res_id.find('[name="aob"]').html(aob)
                            continue
                        }
                        var ele_txt = row_item_template.replaceAll('##count##', i).replaceAll('##size##', size).replaceAll('##offset##', offset).replaceAll('##aob##', aob).replaceAll('##disabled##', aob == '...' ? 'disabled' : '')
                        div_search_result_container.append(ele_txt)
                    }
                    while ($("#result_"+last_index).length > 0) {
                        $("#result_"+last_index).remove()
                        last_index += 1
                    }
                }
                div_search_results.children('.result_row').show()
                div_search_result_container.show()
                row_search_result_count.show()
                btn_download.show()
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                div_search_result_container.hide()
                row_search_result_count.hide()
                btn_download.hide()
                div_search_results.children('.result_row').hide()
                row_aob_initial_search.show()
                break
            case flow_map["FLOW_NO_RESULTS"]:
                row_aob_initial_search.hide()
                div_search_results.children('.result_row').hide()
                div_search_result_container.hide()
                row_search_result_count.show()
                result_count.text(0)
                btn_download.hide()
                break
        }
    }


    function update(component) {
        var name_input = inp_aob_name.val()
        var name_select = sel_aob_name.val()
        var search_type = sel_aob_search_type.val()
        var value = inp_address_value.val()
        var size = sel_value_size.val()
        var range = inp_aob_range.val()
        if (component === sel_aob_name) {
            lookup_name_selected(name_select)
        } else if (component === inp_aob_name) {
            if (aob_list.includes(name_input)) {
                lookup_name_selected(name_input)
            } else if (current_flow === flow_map['FLOW_RESULTS'] || current_flow === flow_map['FLOW_INITIAL_COMPLETE']) {
                lookup_name_selected(name_input)
            }
        }
        update_aob_name(component, name_input, name_select, search_type, value, size, range)
        update_aob_name_list(component, name_input, name_select, search_type, value, size, range)
        update_aob_type(component, name_input, name_select, search_type, value, size, range)
        update_aob_address_value(component, name_input, name_select, search_type, value, size, range)
        update_aob_size(component, name_input, name_select, search_type, value, size, range)
        update_aob_range(component, name_input, name_select, search_type, value, size, range)
        update_aob_search_button(component, name_input, name_select, search_type, value, size, range)
        //update_reset_button(st, ss, value)
        //update_results_progress(st, ss, value)
        //update_results_list(st, ss, value)
    }

    function update_aob_name(_component, _name_input, _name_select, _search_type, _value, _size, _range) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                inp_aob_name.removeAttr('disabled')
                if (_component === sel_aob_name) { //changed by the name select
                    if (_name_select === "_null") {
                        inp_aob_name.val("")
                    } else {
                        inp_aob_name.val(_name_select)
                    }
                } else if (_component == inp_aob_name) { //text was changed

                }
                break
            case flow_map["FLOW_LOOKUP"]:
                inp_aob_name.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                inp_aob_name.removeAttr('disabled')
                if (_component === sel_aob_name) { //changed by the name select
                    if (_name_select === "_null") {
                        inp_aob_name.val("")
                    } else {
                        inp_aob_name.val(_name_select)
                    }
                } else if (_component == inp_aob_name) { //text was changed
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                inp_aob_name.removeAttr('disabled')
                if (_component === sel_aob_name) { //changed by the name select
                    if (_name_select === "_null") {
                        inp_aob_name.val("")
                    } else {
                        inp_aob_name.val(_name_select)
                    }
                } else if (_component == inp_aob_name) { //text was changed

                }
                break
        }
    }

    function update_aob_name_list(_component, _name_input, _name_select, _search_type, _value, _size, _range) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                sel_aob_name.removeAttr('disabled')
                if (_component === inp_aob_name) { //changed by the name input
                    if (aob_list.includes(_name_input)) {
                        sel_aob_name.val(_name_input)
                    } else {
                        sel_aob_name.val("_null")
                    }
                } else if (_component == sel_aob_name) { //text was changed

                }
                break
            case flow_map["FLOW_LOOKUP"]:
                sel_aob_name.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                sel_aob_name.removeAttr('disabled')
                if (_component === inp_aob_name) { //changed by the name input
                    if (aob_list.includes(_name_input)) {
                        sel_aob_name.val(_name_input)
                    } else {
                        sel_aob_name.val("_null")
                    }
                } else if (_component == sel_aob_name) { //text was changed

                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                sel_aob_name.removeAttr('disabled')
                if (_component === inp_aob_name) { //changed by the name input
                    if (aob_list.includes(_name_input)) {
                        sel_aob_name.val(_name_input)
                    } else {
                        sel_aob_name.val("_null")
                    }
                } else if (_component == sel_aob_name) { //text was changed

                }
                break
        }
    }

    function update_aob_type(_component, _name_input, _name_select, _search_type, _value, _size, _range) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                sel_aob_search_type.removeAttr('disabled')
                if (_search_type === 'address') {
                    txt_value_address.text("Address")
                } else {
                    txt_value_address.text("Value")
                }
                break
            case flow_map["FLOW_LOOKUP"]:
                sel_aob_search_type.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                sel_aob_search_type.removeAttr('disabled')
                if (_search_type === 'address') {
                    txt_value_address.text("Address")
                } else {
                    txt_value_address.text("Value")
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                sel_aob_search_type.removeAttr('disabled')
                if (_search_type === 'address') {
                    txt_value_address.text("Address")
                } else {
                    txt_value_address.text("Value")
                }
                break
        }
    }

    function update_aob_address_value(_component, _name_input, _name_select, _search_type, _value, _size, _range) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                inp_address_value.removeAttr('disabled')
                validate_value(_value, _size, _search_type)
                break
            case flow_map["FLOW_LOOKUP"]:
                inp_address_value.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                inp_address_value.removeAttr('disabled')
                validate_value(_value, _size, _search_type)
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                inp_address_value.removeAttr('disabled')
                validate_value(_value, _size, _search_type)
                break
            case flow_map["FLOW_NO_RESULTS"]:
                inp_address_value.removeAttr('disabled')
                validate_value(_value, _size, _search_type)
                break
        }
        if (_component == sel_aob_search_type) {
            inp_address_value.attr('inputmode', _search_type === 'value' ? 'decimal' : 'text')
        }
    }

    function update_aob_size(_component, _name_input, _name_select, _search_type, _value, _size, _range) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                sel_value_size.removeAttr('disabled')
                if (_search_type == 'address') {
                    sel_value_size.hide()
                } else {
                    sel_value_size.show()
                }
                break
            case flow_map["FLOW_LOOKUP"]:
                sel_value_size.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                sel_value_size.removeAttr('disabled')
                if (_search_type == 'address') {
                    sel_value_size.hide()
                } else {
                    sel_value_size.show()
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                sel_value_size.removeAttr('disabled')
                if (_search_type == 'address') {
                    sel_value_size.hide()
                } else {
                    sel_value_size.show()
                }
                break
        }
    }

    function update_aob_range(_component, _name_input, _name_select, _search_type, _value, _size, _range) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                inp_aob_range.removeAttr('disabled')
                validate_range(_range)
                break
            case flow_map["FLOW_LOOKUP"]:
                inp_aob_range.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                inp_aob_range.removeAttr('disabled')
                validate_range(_range)
                break
            case flow_map["FLOW_NO_RESULTS"]:
                inp_aob_range.removeAttr('disabled')
                validate_range(_range)
                break
        }
    }

    function update_aob_search_button(_component, _name_input, _name_select, _search_type, _value, _size, _range) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                if (value_valid && range_valid && _name_input.length > 0) {
                    btn_search.removeAttr('disabled')
                    if (_search_type === 'address') {
                        switch_repeat.removeAttr('disabled')
                    } else {
                        switch_repeat.prop('checked', false)
                        switch_repeat.attr('disabled', 'disabled')
                    }
                } else {
                    btn_search.attr('disabled', 'disabled')
                    switch_repeat.attr('disabled', 'disabled')
                }
                break
            case flow_map["FLOW_LOOKUP"]:
                btn_search.attr('disabled', 'disabled')
                switch_repeat.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                if (value_valid && range_valid && _name_input.length > 0) {
                    btn_search.removeAttr('disabled')
                    if (_search_type === 'address') {
                        switch_repeat.removeAttr('disabled')
                    } else {
                        switch_repeat.prop('checked', false)
                        switch_repeat.attr('disabled', 'disabled')
                    }
                } else {
                    btn_search.attr('disabled', 'disabled')
                    switch_repeat.attr('disabled', 'disabled')
                }
                break
            case flow_map["FLOW_INITIAL_COMPLETE"]:
                if (value_valid && _name_input.length > 0) {
                    btn_search.removeAttr('disabled')
                    if (_search_type === 'address') {
                        switch_repeat.removeAttr('disabled')
                    } else {
                        switch_repeat.prop('checked', false)
                        switch_repeat.attr('disabled', 'disabled')
                    }
                } else {
                    btn_search.attr('disabled', 'disabled')
                    switch_repeat.attr('disabled', 'disabled')
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                btn_search.attr('disabled', 'disabled')
                switch_repeat.attr('disabled', 'disabled')
                break
        }
    }

    function lookup_name_selected(name) {
        current_flow = flow_map['FLOW_LOOKUP']
        value_valid = false
        $.send('/aob', { "command": "AOB_SELECT", "name": name }, on_aob_status)
    }

    function validate_value(_value, _size, _type) {
        if (_value === "") {
            value_valid = false
            return
        }
        if (_type === 'address') {
            value_valid = /^(?!.{256,})(?!(aux|clock\$|con|nul|prn|com[1-9]|lpt[1-9])(?:$|\.))[^ ][ \.\w-$()+=[\];#@~,&amp;']+[^\. ]:\d+\+[0-9a-f]+$/i.test(_value) || /^[0-9A-F]{5,16}$/i.test(_value)
        } else {
            var n = Number(_value)
            switch (_size) {
                case 'byte_1':
                    value_valid = (n >= -2<<6 && n < 2<<7)
                    break
                case 'byte_2':
                    value_valid = (n >= -2<<14 && n < 2<<15)
                    break
                case 'byte_4':
                    value_valid = (n >= -2<<30 && n < 2**32)
                    break
            }
        }
    }

    function validate_range(_value) {
        if (_value === "") {
            range_valid = false
            return
        }
        if (!Number.isInteger(Number(_value))) {
            range_valid = false
        } else {
            var n = Number(_value)
            range_valid = n >= 20 && (n % 2) == 0
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

    function has(target, path) {
        if (typeof target != 'object' || target == null) {
            return false;
        }
        var parts = path.split('.');

        while(parts.length) {
            var branch = parts.shift();
            if (!(branch in target)) {
                return false;
            }

            target = target[branch];
        }
        return true;
    }

}( window.aob = window.aob || {}, jQuery ));







