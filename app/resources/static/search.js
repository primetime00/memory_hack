(function( search, $, undefined ) {
    //Private Property
    var flow_map = {"FLOW_START": 4, "FLOW_SEARCHING": 6, "FLOW_RESULTS": 0, "FLOW_NO_RESULTS": 2, "FLOW_INITIALIZE_UNKNOWN": 1}
    var current_flow = flow_map["FLOW_START"]
    var sel_search_process;
    var div_search_block;
    var div_search_information_block;
    var row_search_type;
    var sel_search_type;
    var row_search_size;
    var sel_search_size;
    var row_search_value;
    var inp_search_value;
    var row_search_direction;
    var sel_search_direction;
    var btn_search_button;
    var btn_reset_button;
    var div_search_results;
    var list_search_result_list;
    var result_count;
    var result_count_disclaimer;
    var row_search_progress;
    var row_search_initialize_unknown;
    var search_progress;

    var li_template = (['<ons-list-item class="result-row">',
          '<ons-row>',
            '<ons-col align="center" width="65%" class="col ons-col-inner">',
              '<ons-row>',
                '<ons-col width="100%" align="center" class="col ons-col-inner address">##address##</ons-col>',
              '</ons-row>',
              '<ons-row>',
                '<ons-col width="100%" align="center" class="col ons-col-inner"><input tabIndex="-1" type="text" id="result_value_##index##" data-address="##address##" name="search_value" class="text-input text-input--material r-value" value="##value##" onkeydown="search.result_change(this)" onblur="search.result_change(this)" autocomplete="chrome-off"></ons-col>',
              '</ons-row>',
            '</ons-col>',
            '<ons-col align="center" width="7%" class="col ons-col-inner">',
                '<label class="checkbox checkbox--material"><input tabIndex="-1" id="search_freeze_##index##" type="checkbox" class="checkbox__input checkbox--material__input freeze" data-address="##address##" onchange="search.result_freeze(this, ##index##)"> <div class="checkbox__checkmark checkbox--material__checkmark"></div>',
            '</ons-col>',
            '<ons-col align="center" width="18%" class="col ons-col-inner">',
                '<ons-col align="center" width="98px" class="col ons-col-inner"><ons-button modifier="quiet" name="add_button" data-address="##address##" onclick="search.copy_result(##index##, this)">Copy</ons-button></ons-col>',
            '</ons-col>',
          '</ons-row>',
      '</ons-list-item>',
    ]).join("\n");


    var current_state = "SEARCH_STATE_START";
    var current_search_type = "exact";
    var current_search_round = 0;
    var current_search_results = []
    var current_process = ""
    var initialized = false
    var value_valid = false
    search.updater = null


    //Public Property

    //Public Method
    search.search_type_changed = function(option) {
        update()
    };

    search.search_size_changed = function(option) {
        update()
    };

    search.search_value_changed = function(value) {
        update()
    }

    search.result_change = function(ele) {
        if(event.key === 'Enter' || event.key === 'Return' || event.keyCode == 13) {
            $.send('/search', {'command': 'SEARCH_WRITE', 'address': ele.dataset.address, 'value': ele.value}, on_search_status)
            ele.blur()
        }
    }

    search.result_freeze = function(ele, index) {
        $.send('/search', {'command': 'SEARCH_FREEZE', 'address': ele.dataset.address, 'freeze': ele.checked}, on_search_status)
    }

    search.on_return_pressed = function(ele) {
        if (!btn_search_button.prop('disabled')) {
            if(event.key === 'Enter' || event.key === 'Return' || event.keyCode == 13) {
                search.on_search_clicked()
                ele.blur()
            }
        }
    }

    search.on_search_clicked = function() {
        var size = sel_search_size.val()
        var type = sel_search_type.val()
        if (type === 'unknown_near') {
            size = 'address'
        }
        $.send('/search',
        {   "command": "SEARCH_START",
            "size": size,
            "type": type,
            "value": inp_search_value.val(),
         }
        , on_search_status);
        current_flow = flow_map["FLOW_SEARCHING"]
        update()
    };

    search.on_reset_clicked = function() {
        btn_reset_button.attr('disabled', 'disabled')
        btn_search_button.attr('disabled', 'disabled')
        $("input.freeze").prop( "checked", false );
        $.send('/search', { "command": "SEARCH_RESET" }, on_search_status);
    };

    search.on_process_changed = function(process) {
        process_control.request_process(process, 'search', function(result){
            if (!result.success) {
                set_process('_null')
                ons.notification.toast(result.error, { timeout: 4000, animation: 'fall' })
            } else {
                set_process(process)
            }
        })
    };

    search.on_update_process_list = function(process_list_add, process_list_remove) {
        var options = sel_search_process.children('option') ;
        var selected = sel_search_process.find('option:selected')
        if (process_list_remove.includes(selected.val())) {
            div_search_block.hide()
        }
        for (var i=options.length-1; i>=0; i--) {
            var option=options[i]
            if (process_list_remove.includes(option.value)) {
                option.remove()
            }
        }
        var f = sel_search_process.find('option:first')
        for (const item of process_list_add) {
            f.after($('<option>', {value: item, text: item}))
        }
    }

    search.on_update_selected_process = function(process_name) {
        var value = sel_search_process.val()
        if (value != process_name){
            set_process(process_name)
        }
    }

    search.on_tab_set = function(tab) {
        if (tab !== 'search') {
            if (search.updater !== null) {
                clearTimeout(search.updater)
                search.updater = null
            }
        } else {
            if (search.updater === null && current_flow === flow_map["FLOW_RESULTS"]) {
                search.updater = setTimeout(request_update, 100)
            }
        }
    };


    search.ready = function()  {
      initialize()
      $('#search_value_div').show()
      $('#search_direction_div').hide()
      $('#search_results').hide();
      $('#search_searching').hide();
      $('#search_result_table').hide();
      $('#search_reset_button').prop("disabled",true);
      $('#search_button').prop("disabled",true);
      $("#search_paste_button").hide()

      list_search_result_list.children("ons-list-item").remove()
      for (i=0; i<40; i++) {
        var el = ons.createElement(li_template.replaceAll('##index##', i).replaceAll('##address##', 0).replaceAll('##value##', 0))
        list_search_result_list.append(el)
      }
    };

    search.copy_result = function(index, element) {
        document.clipboard.copy({'address': current_search_results[index].address.toString(16), 'value': {'Actual': current_search_results[index].value, 'Display': current_search_results[index].value.toString()}})
    }

    search.clipboard_data_copied = function(data) {
        if (has(data, 'aob') || has(data, 'value')) {
            $("#search_paste_button").show()
        }
    }
    search.clipboard_data_pasted = function(data) {
        if (sel_search_type.val() === 'unknown_near') {
            if (has(data, 'resolved')) {
                inp_search_value.val(data.resolved)
                update()
                return
            }
            if (has(data, 'address')) {
                inp_search_value.val(data.address)
                update()
                return
            }
        }
        if (sel_search_size.val() === 'array') {
            if (has(data, 'aob')) {
                inp_search_value.val(data.aob)
            } else {
                sel_search_size.val('byte_4')
                update()
                inp_search_value.val(data.value.Display)
            }
            update()
        } else {
            if (has(data, 'value')) {
                inp_search_value.val(data.value.Display)
            } else {
                sel_search_size.val('array')
                update()
                inp_search_value.val(data.aob)
            }
            update()
        }
    }

    search.clipboard_data_cleared = function() {
        $("#search_paste_button").hide()
    }


    //Private Methods
    function on_search_ready() {
        $.send('/search', { "command": "SEARCH_INITIALIZE" }, on_search_status);
    }

    function set_process(process_name) {
        sel_search_process.val(process_name)
        if (process_name === '_null') {
            process_name = ''
        }
        if (process_name.length > 0) {
            div_search_block.show()
            on_search_ready()
        } else {
            div_search_block.hide()
        }
    }

    function on_search_status(result) {
        current_flow = has(result, 'flow') ? result.flow : current_flow
        var repeat = result.repeat || 0
        result.has_error = result.hasOwnProperty('error') && result.error !== ""
        result.error = result.error || ""
        setup_search_type(result)
        setup_search_size(result)
        setup_search_value(result)
        setup_search_button(result)
        setup_reset_button(result)
        setup_results_progress(result)
        setup_results_list(result)
        if (result.error !== "") {
            ons.notification.toast(result.error, { timeout: 5000, animation: 'fall' })
        }
        if (repeat > 0) {
            setTimeout(function(){
                $.send('/search', { "command": "SEARCH_STATUS" }, on_search_status);
            }, repeat);
        }
        console.log('aaa1')
        if (search.updater === null && current_flow === flow_map["FLOW_RESULTS"]) {
            console.log('aaa2')
            search.updater = setTimeout(request_update, 1000)
        } else if (search.updater !== null && current_flow !== flow_map["FLOW_RESULTS"]) {
            clearTimeout(search.updater)
            search.updater = null
        }
    }

    function request_update() {
        $.send('/search', { "command": "SEARCH_RESULT_UPDATE" }, function(result){
            current_flow = has(result, 'flow') ? result.flow : current_flow
            if (current_flow === flow_map["FLOW_RESULTS"]){
                setup_results_list(result)
                if (result.repeat > 0) {
                    search.updater = setTimeout(request_update, result.repeat)
                }
            }
        });
    }

    function setup_search_type(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                sel_search_type.removeAttr('disabled')
                sel_search_type.find('option[value="equal_to"]').show()
                sel_search_type.find('option[value="greater_than"]').show()
                sel_search_type.find('option[value="less_than"]').show()
                sel_search_type.find('option[value="unknown"]').show()
                sel_search_type.find('option[value="unknown_near"]').show()
                sel_search_type.find('option[value="increase"]').hide()
                sel_search_type.find('option[value="decrease"]').hide()
                sel_search_type.find('option[value="unchanged"]').hide()
                sel_search_type.find('option[value="changed"]').hide()
                sel_search_type.find('option[value="changed_by"]').hide()
                sel_search_type.find('option[value="equal_to"]').prop('selected', true)
                if (has(result, "type")) {
                    sel_search_type.val(result.type)
                }
                break
            case flow_map["FLOW_SEARCHING"]:
                sel_search_type.attr('disabled', 'disabled')
                if (has(result, "type")) {
                    sel_search_type.val(result.type)
                }
                break
            case flow_map["FLOW_RESULTS"]:
                sel_search_type.removeAttr('disabled')
                if (has(result, 'size') && result.size === 'array'){
                    sel_search_type.find('option[value="equal_to"]').show()
                    sel_search_type.find('option[value="greater_than"]').hide()
                    sel_search_type.find('option[value="less_than"]').hide()
                    sel_search_type.find('option[value="unknown"]').hide()
                    sel_search_type.find('option[value="unknown_near"]').hide()
                    sel_search_type.find('option[value="increase"]').hide()
                    sel_search_type.find('option[value="decrease"]').hide()
                    sel_search_type.find('option[value="unchanged"]').show()
                    sel_search_type.find('option[value="changed"]').show()
                    sel_search_type.find('option[value="changed_by"]').hide()
                    sel_search_type.find('option[value="equal_to"]').prop('selected', true)
                } else {
                    sel_search_type.find('option[value="equal_to"]').show()
                    sel_search_type.find('option[value="greater_than"]').show()
                    sel_search_type.find('option[value="less_than"]').show()
                    sel_search_type.find('option[value="unknown"]').hide()
                    sel_search_type.find('option[value="unknown_near"]').hide()
                    sel_search_type.find('option[value="increase"]').show()
                    sel_search_type.find('option[value="decrease"]').show()
                    sel_search_type.find('option[value="unchanged"]').show()
                    sel_search_type.find('option[value="changed"]').show()
                    sel_search_type.find('option[value="changed_by"]').show()
                    sel_search_type.find('option[value="equal_to"]').prop('selected', true)
                }
                if (has(result, "type")) {
                    sel_search_type.val(result.type)
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                sel_search_type.attr('disabled', 'disabled')
                if (has(result, "type")) {
                    sel_search_type.val(result.type)
                }
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                sel_search_type.removeAttr('disabled')
                sel_search_type.find('option[value="equal_to"]').hide()
                sel_search_type.find('option[value="greater_than"]').hide()
                sel_search_type.find('option[value="less_than"]').hide()
                sel_search_type.find('option[value="unknown"]').hide()
                sel_search_type.find('option[value="unknown_near"]').hide()
                sel_search_type.find('option[value="increase"]').show()
                sel_search_type.find('option[value="decrease"]').show()
                sel_search_type.find('option[value="unchanged"]').show()
                sel_search_type.find('option[value="changed"]').show()
                sel_search_type.find('option[value="changed_by"]').show()
                sel_search_type.find('option[value="increase"]').prop('selected', true)
                break
        }
    }

    function setup_search_size(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                if (has(result, 'type') && (result.type === 'unknown' || result.type === 'unknown_near')) {
                    row_search_size.hide()
                } else {
                    row_search_size.show()
                    sel_search_size.removeAttr('disabled')
                    sel_search_size.find('option[value="byte_1"]').show()
                    sel_search_size.find('option[value="byte_2"]').show()
                    sel_search_size.find('option[value="byte_4"]').show()
                    sel_search_size.find('option[value="float"]').show()
                    sel_search_size.find('option[value="array"]').show()
                    sel_search_size.find('option[value="byte_4"]').prop('selected', true)
                    if (has(result, "size")) {
                        sel_search_size.val(result.size)
                    }
                }
                break
            case flow_map["FLOW_SEARCHING"]:
                sel_search_size.attr('disabled', 'disabled')
                if (has(result, "size")) {
                    sel_search_size.val(result.size)
                }
                break
            case flow_map["FLOW_RESULTS"]:
                sel_search_size.removeAttr('disabled')
                if (has(result, 'size') && result.size === 'array'){
                    sel_search_size.find('option[value="byte_1"]').hide()
                    sel_search_size.find('option[value="byte_2"]').hide()
                    sel_search_size.find('option[value="byte_4"]').hide()
                    sel_search_size.find('option[value="float"]').hide()
                    sel_search_size.find('option[value="array"]').hide()
                    sel_search_size.find('option[value="array"]').prop('selected', true)
                } else {
                    sel_search_size.find('option[value="byte_1"]').show()
                    sel_search_size.find('option[value="byte_2"]').show()
                    sel_search_size.find('option[value="byte_4"]').show()
                    sel_search_size.find('option[value="float"]').show()
                    sel_search_size.find('option[value="array"]').hide()
                    sel_search_size.find('option[value="byte_4"]').prop('selected', true)
                }
                if (has(result, "size")) {
                    sel_search_size.val(result.size)
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                sel_search_size.attr('disabled', 'disabled')
                if (has(result, "size")) {
                    sel_search_size.val(result.size)
                }
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                sel_search_size.removeAttr('disabled')
                sel_search_size.find('option[value="byte_1"]').show()
                sel_search_size.find('option[value="byte_2"]').show()
                sel_search_size.find('option[value="byte_4"]').show()
                sel_search_size.find('option[value="float"]').show()
                sel_search_size.find('option[value="array"]').hide()
                sel_search_size.find('option[value="byte_4"]').prop('selected', true)
                if (has(result, "size")) {
                    sel_search_size.val(result.size)
                }
                row_search_size.show()
                break
        }
    }

    function setup_search_value(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                inp_search_value.removeAttr('disabled')
                if (has(result, 'type') && result.type === 'unknown') {
                    value_valid = true
                    row_search_value.hide()
                }else {
                    row_search_value.show()
                    if (has(result, "value") && has(result, "size")) {
                        inp_search_value.val(result.value)
                        validate_value(String(result.value), result.size, result.type)
                    }else {
                        inp_search_value.val("")
                        value_valid = false
                    }
                }
                break
            case flow_map["FLOW_SEARCHING"]:
                inp_search_value.attr('disabled', 'disabled')
                if (has(result, "value") && has(result, "size")) {
                    inp_search_value.val(result.value)
                    validate_value(String(result.value), result.size, result.type)
                }else {
                    inp_search_value.val("")
                    value_valid = false
                }
                break
            case flow_map["FLOW_RESULTS"]:
                inp_search_value.removeAttr('disabled')
                if (has(result, "value") && has(result, "size")) {
                    inp_search_value.val(result.value)
                    validate_value(String(result.value), result.size, result.type)
                }else {
                    inp_search_value.val("")
                    value_valid = false
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                inp_search_value.attr('disabled', 'disabled')
                if (has(result, "value") && has(result, "size")) {
                    inp_search_value.val(result.value)
                    validate_value(String(result.value), result.size, result.type)
                }else {
                    inp_search_value.val("")
                    value_valid = false
                }
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                row_search_value.hide()
                break
        }
    }

    function setup_search_button(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                btn_search_button.attr('disabled', 'disabled')
                if (has(result, 'type') && result.type == 'unknown') {
                    btn_search_button.removeAttr('disabled')
                } else {
                    if (value_valid) {
                        btn_search_button.removeAttr('disabled')
                    } else {
                        btn_search_button.attr('disabled', 'disabled')
                    }
                }
                break
            case flow_map["FLOW_SEARCHING"]:
                btn_search_button.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                btn_search_button.attr('disabled', 'disabled')
                if (has(result, 'type') && (result.type == 'unknown' || result.type == 'unknown_near' || result.type == 'increase' || result.type == 'decrease' || result.type == 'changed' || result.type == 'unchanged')) {
                    btn_search_button.removeAttr('disabled')
                } else {
                    if (value_valid) {
                        btn_search_button.removeAttr('disabled')
                    } else {
                        btn_search_button.attr('disabled', 'disabled')
                    }
                }
                break
            case flow_map["FLOW_NO_RESULTS"]:
                btn_search_button.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                btn_search_button.removeAttr('disabled')
                break
        }
    }

    function setup_reset_button(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                btn_reset_button.attr('disabled', 'disabled')
                btn_reset_button.text('Reset')
                break
            case flow_map["FLOW_SEARCHING"]:
                btn_reset_button.text("Stop")
                btn_reset_button.removeAttr('disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                btn_reset_button.removeAttr('disabled')
                btn_reset_button.text('Reset')
                break
            case flow_map["FLOW_NO_RESULTS"]:
                btn_reset_button.text("Reset")
                btn_reset_button.removeAttr('disabled')
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                btn_reset_button.text("Reset")
                btn_reset_button.removeAttr('disabled')
                break
        }
    }

    function setup_results_progress(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                div_search_results.hide()
                row_search_progress.hide()
                row_search_initialize_unknown.hide()
                break
            case flow_map["FLOW_SEARCHING"]:
                div_search_results.show()
                row_search_progress.show()
                row_search_initialize_unknown.hide()
                search_progress.text(result.progress)
                break
            case flow_map["FLOW_RESULTS"]:
                div_search_results.show()
                row_search_initialize_unknown.hide()
                row_search_progress.hide()
                break
            case flow_map["FLOW_NO_RESULTS"]:
                div_search_results.show()
                row_search_initialize_unknown.hide()
                row_search_progress.hide()
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                div_search_results.show()
                row_search_progress.hide()
                row_search_initialize_unknown.show()
                break
        }
    }
    function setup_results_list(result) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                div_search_results.hide()
                list_search_result_list.hide()
                break
            case flow_map["FLOW_SEARCHING"]:
                div_search_results.show()
                list_search_result_list.hide()
                break
            case flow_map["FLOW_RESULTS"]:
                div_search_results.show()
                list_search_result_list.show()
                result_count.text(result.count)
                if (result.count > 40) {
                    result_count_disclaimer.show()
                } else {
                    result_count_disclaimer.hide()
                }
                populate_results(result.results, result.array)
                break
            case flow_map["FLOW_NO_RESULTS"]:
                div_search_results.show()
                list_search_result_list.show()
                result_count.text(0)
                result_count_disclaimer.hide()
                populate_results([], false)
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                div_search_results.show()
                list_search_result_list.hide()
                result_count.text(0)
                result_count_disclaimer.hide()
                break
        }
    }

    function update() {
        var st = sel_search_type.val()
        var ss = sel_search_size.val()
        var value = inp_search_value.val()
        update_search_type(st, ss, value)
        update_search_size(st, ss, value)
        update_search_value(st, ss, value)
        update_search_button(st, ss, value)
        update_reset_button(st, ss, value)
        update_results_progress(st, ss, value)
        update_results_list(st, ss, value)
    }

    function update_search_type(_type, _size, _value) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                sel_search_type.removeAttr('disabled')
                switch (_size) {
                    case 'array':
                        row_search_type.show()
                        sel_search_type.find('option[value="equal_to"]').prop('selected', true)
                        sel_search_type.find('option[value!="equal_to"]').hide()
                        break
                    default:
                        row_search_type.show()
                        sel_search_type.find('option[value="equal_to"]').show()
                        sel_search_type.find('option[value="greater_than"]').show()
                        sel_search_type.find('option[value="less_than"]').show()
                        sel_search_type.find('option[value="unknown"]').show()
                        sel_search_type.find('option[value="unknown_near"]').show()
                        sel_search_type.find('option[value="increase"]').hide()
                        sel_search_type.find('option[value="decrease"]').hide()
                        sel_search_type.find('option[value="unchanged"]').hide()
                        sel_search_type.find('option[value="changed"]').hide()
                        sel_search_type.find('option[value="changed_by"]').hide()
                        break
                }
                break
            case flow_map["FLOW_SEARCHING"]:
                sel_search_type.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                sel_search_type.removeAttr('disabled')
                switch (_size) {
                    case 'array':
                        row_search_type.show()
                        sel_search_type.find('option[value="equal_to"]').show()
                        sel_search_type.find('option[value="greater_than"]').hide()
                        sel_search_type.find('option[value="less_than"]').hide()
                        sel_search_type.find('option[value="unknown"]').hide()
                        sel_search_type.find('option[value="unknown_near"]').hide()
                        sel_search_type.find('option[value="increase"]').hide()
                        sel_search_type.find('option[value="decrease"]').hide()
                        sel_search_type.find('option[value="unchanged"]').show()
                        sel_search_type.find('option[value="changed"]').show()
                        sel_search_type.find('option[value="changed_by"]').hide()

                        break
                    default:
                        row_search_type.show()
                        sel_search_type.find('option[value="equal_to"]').show()
                        sel_search_type.find('option[value="greater_than"]').show()
                        sel_search_type.find('option[value="less_than"]').show()
                        sel_search_type.find('option[value="unknown"]').hide()
                        sel_search_type.find('option[value="unknown_near"]').hide()
                        sel_search_type.find('option[value="increase"]').show()
                        sel_search_type.find('option[value="decrease"]').show()
                        sel_search_type.find('option[value="unchanged"]').show()
                        sel_search_type.find('option[value="changed"]').show()
                        sel_search_type.find('option[value="changed_by"]').show()
                        break
                }
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                sel_search_type.removeAttr('disabled')
                sel_search_type.find('option[value="equal_to"]').hide()
                sel_search_type.find('option[value="greater_than"]').hide()
                sel_search_type.find('option[value="less_than"]').hide()
                sel_search_type.find('option[value="unknown"]').hide()
                sel_search_type.find('option[value="unknown_near"]').hide()
                sel_search_type.find('option[value="increase"]').show()
                sel_search_type.find('option[value="decrease"]').show()
                sel_search_type.find('option[value="unchanged"]').show()
                sel_search_type.find('option[value="changed"]').show()
                sel_search_type.find('option[value="changed_by"]').show()
                break
        }
    }

    function update_search_size(_type, _size, _value) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                sel_search_size.removeAttr('disabled')
                switch (_type) {
                    case 'equal_to':
                        row_search_size.show()
                        sel_search_size.find('option[value="array"]').show()
                        break
                    case 'unknown':
                    case 'unknown_near':
                        row_search_size.hide()
                        break
                    default:
                        row_search_size.show()
                        sel_search_size.find('option[value="array"]').hide()
                        break
                }
                break
            case flow_map["FLOW_SEARCHING"]:
                sel_search_size.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                sel_search_size.removeAttr('disabled')
                row_search_size.show()
                sel_search_size.find('option[value="array"]').hide()
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                sel_search_size.removeAttr('disabled')
                sel_search_size.find('option[value="byte_1"]').show()
                sel_search_size.find('option[value="byte_2"]').show()
                sel_search_size.find('option[value="byte_4"]').show()
                sel_search_size.find('option[value="float"]').show()
                sel_search_size.find('option[value="array"]').hide()
                break
        }
    }

    function update_search_value(_type, _size, _value) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                inp_search_value.removeAttr('disabled')
                if (_type == 'unknown_near') {
                    $("#value_header").text("Address")
                } else {
                    $("#value_header").text("Value")
                }
                if (_type == 'unknown') {
                    row_search_value.hide()
                    value_valid = true
                } else {
                    row_search_value.show()
                    inp_search_value.attr('inputmode', _size === 'array' ? 'text' : 'decimal')
                    validate_value(_value, _size, _type)
                }
                break
            case flow_map["FLOW_SEARCHING"]:
                inp_search_value.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                inp_search_value.removeAttr('disabled')
                if (_type == 'increase' || _type == 'decrease' || _type == 'changed' || _type == 'unchanged') {
                    row_search_value.hide()
                    value_valid = true
                } else {
                    row_search_value.show()
                    inp_search_value.attr('inputmode', _size === 'array' ? 'text' : 'decimal')
                    validate_value(_value, _size, _type)
                }
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                $("#value_header").text("Value")
                if (_type == 'changed_by') {
                    inp_search_value.removeAttr('disabled')
                    row_search_value.show()
                    inp_search_value.attr('inputmode', _size === 'array' ? 'text' : 'decimal')
                    validate_value(_value, _size, _type)
                }
                else {
                    row_search_value.hide()
                    value_valid = true
                }
                break
        }
    }

    function update_search_button(_type, _size, _value) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                if (_type == 'unknown') {
                    btn_search_button.removeAttr('disabled')
                } else {
                    if (value_valid) {
                        btn_search_button.removeAttr('disabled')
                    } else {
                        btn_search_button.attr('disabled', 'disabled')
                    }
                }
                break
            case flow_map["FLOW_SEARCHING"]:
                btn_search_button.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                if (_type == 'unknown') {
                    btn_search_button.removeAttr('disabled')
                } else {
                    if (value_valid) {
                        btn_search_button.removeAttr('disabled')
                    } else {
                        btn_search_button.attr('disabled', 'disabled')
                    }
                }
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                if (_type !== 'changed_by') {
                    btn_search_button.removeAttr('disabled')
                } else {
                    if (value_valid) {
                        btn_search_button.removeAttr('disabled')
                    } else {
                        btn_search_button.attr('disabled', 'disabled')
                    }
                }
                break
        }
    }

    function update_reset_button(_type, _size, _value) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                btn_reset_button.text("Reset")
                btn_reset_button.attr('disabled', 'disabled')
                break
            case flow_map["FLOW_SEARCHING"]:
                btn_reset_button.text("Stop")
                btn_reset_button.removeAttr('disabled')
                break
            case flow_map["FLOW_RESULTS"]:
                btn_reset_button.text("Reset")
                btn_reset_button.removeAttr('disabled')
                break
            case flow_map["FLOW_INITIALIZE_UNKNOWN"]:
                btn_reset_button.text("Reset")
                btn_reset_button.removeAttr('disabled')
                break
        }
    }
    function update_results_progress(_type, _size, _value) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                div_search_results.hide()
                break
            case flow_map["FLOW_SEARCHING"]:
                div_search_results.show()
                search_progress.text('0')
                break
        }
    }

    function update_results_list(_type, _size, _value) {
        switch (current_flow) {
            case flow_map["FLOW_START"]:
                div_search_results.hide()
                break
            case flow_map["FLOW_SEARCHING"]:
                list_search_result_list.hide()
                break
        }
    }


    function validate_value(_value, _size, _type) {
        if (_value === "") {
            value_valid = false
            return
        }
        if (_type == 'unknown_near') {
            value_valid = /^[0-9A-F]{5,16}$/i.test(_value)
            return
        }
        const array_regex = new RegExp('^(?:([0-9A-F]{2}|\\?{2}) )*([0-9A-F]{2}|\\?{2})$');
        if (_size == 'array') {
            value_valid = array_regex.test(_value.toUpperCase())
        } else if (_size == 'float') {
             value_valid = !isNaN(parseFloat(_value)) && isFinite(_value);
        } else {
            if (!Number.isInteger(Number(_value))) {
                value_valid = false
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
    }

    function populate_results(results, is_array) {
        current_search_results = results
        var elements = $(".result-row")
        for (i=0; i<40; i++) {
            var el = $(elements[i])
            if (i < results.length) {
                var item = results[i]
                var address_element = el.find(".address")
                var value_element = el.find("input[name='search_value']")
                var add_element = el.find("ons-button")
                var freeze_element = el.find(".freeze")
                value_element.attr('inputmode', is_array ? 'text' : 'decimal')
                if (value_element.is(":focus")) {
                    continue
                }
                var addr = (item.address).toString(16).toUpperCase().padStart(16, '0')
                if (address_element.text() !== addr) {
                    address_element.text((item.address).toString(16).toUpperCase().padStart(16, '0'))
                }
                value_element.attr('data-address', item.address)
                freeze_element.attr('data-address', item.address)
                add_element.attr('data-address', item.address)
                value_element.val(item.value)
                el.show()
            } else {
                el.hide()
            }

        }
    }

    function initialize() {
        sel_search_process = $("#search_process")
        div_search_block = $("#search_block")
        div_search_information_block = $("#search_information_block")
        row_search_size = $("#row_search_size");
        sel_search_size = $("#search_size");
        row_search_type = $("#row_search_type");
        sel_search_type = $("#search_type");
        row_search_value = $("#row_search_value");
        inp_search_value = $("#search_value");
        row_search_direction = $("#search_direction_row");
        sel_search_direction = $("#search_direction");
        btn_search_button = $("#search_button");
        btn_reset_button = $("#search_reset_button");
        div_search_results = $("#search_results");
        list_search_result_list = $("#search_result_list");
        result_count = $("#result_count")
        result_count_disclaimer = $("#result_count_disclaimer")
        row_search_initialize_unknown = $("#search_initialize_unknown_row")
        row_search_progress = $("#search_progress_row")
        search_progress = $("#search_progress")

        //$.send('/search', { "command": "SEARCH_INITIALIZE" }, on_search_status);
    };

    function on_unknown_search_selected() {
        switch (current_state) {
            case 'SEARCH_STATE_START':
                hide([row_search_value, row_search_direction])
                disable([$(sel_search_size.children("[value='array']"))])
                break;
            case 'SEARCH_STATE_SEARCHING':
                break;
            case 'SEARCH_STATE_CONTINUE':
                break;
        }
    }

    function on_value_search_selected() {
        switch (current_state) {
            case 'SEARCH_STATE_START':
                hide([row_search_direction])
                show([row_search_value])
                enable([$(sel_search_size.children("[value='array']"))])
                break;
            case 'SEARCH_STATE_SEARCHING':
                break;
            case 'SEARCH_STATE_CONTINUE':
                break;
        }
    }

    function on_process_changed(process) {
        switch (current_state) {
            case 'SEARCH_STATE_START':
                setup_start_state()
                break;
            case 'SEARCH_STATE_SEARCHING':
                $.send('/search', { "command": "SEARCH_RESET" }, on_search_status);
                break;
            case 'SEARCH_STATE_CONTINUE':
                $.send('/search', { "command": "SEARCH_RESET" }, on_search_status);
                break;
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

}( window.search = window.search || {}, jQuery ));
