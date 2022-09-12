(function( search, $, undefined ) {
    //Private Property
    var div_search_information_block;
    var sel_search_size;
    var sel_search_type;
    var row_search_value;
    var inp_search_value;
    var row_search_direction;
    var sel_search_direction;
    var btn_search_button;
    var btn_reset_button;
    var div_search_results;
    var row_search_result_list;
    var result_count;
    var result_count_disclaimer;
    var row_search_progress;
    var search_progress;

    var li_template = (['<ons-list-item class="result-row">',
          '<ons-row>',
            '<ons-col align="center" width="190px" class="col ons-col-inner address">##address##</ons-col>',
            '<ons-col align="center" width="190px" class="col ons-col-inner"><input type="text" id="result_value_##index##" data-address="##address##" name="search_value" class="text-input text-input--material value" value="##value##" onkeydown="search.result_change(this)"></ons-col>',
            '<ons-col align="center" class="col ons-col-inner">',
              '<label class="checkbox checkbox--material" style="padding-left: 10px">',
                '<input type="checkbox" id="freeze_result_value_##index##" class="checkbox__input checkbox--material__input freeze" data-address="##address##" onclick="search.result_freeze(this)">',
                '<div class="checkbox__checkmark checkbox--material__checkmark"></div>',
                'Freeze',
              '</label>',
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


    //Public Property

    //Public Method
    search.search_type_changed = function(option) {
      current_search_type = option;
      if (option == 'unknown') {
        on_unknown_search_selected()
      } else {
        on_value_search_selected()
      }
    };

    search.result_change = function(ele) {
        if(event.key === 'Enter') {
            $.send('/search', {'command': 'SEARCH_WRITE', 'address': ele.dataset.address, 'value': ele.value}, on_search_status)
            ele.blur()
        }
    }
    search.result_freeze = function(ele) {
        $.send('/search', {'command': 'SEARCH_FREEZE', 'address': ele.dataset.address, 'freeze': ele.checked}, on_search_status)
    }

    search.on_search_clicked = function() {
        $.send('/search',
        {   "command": "SEARCH_START",
            "size": sel_search_size.val(),
            "type": sel_search_type.val(),
            "value": inp_search_value.val(),
            "direction": sel_search_direction.val()
         }
        , on_search_status);
        setup_searching_state()
    };

    search.on_reset_clicked = function() {
        $.send('/search', { "command": "SEARCH_RESET" }, on_search_status);
    };

    search.on_process_changed = function(process) {
        if (process !== current_process) {
            current_process = process
            on_process_changed(process)
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

      row_search_result_list.children("ons-list-item").remove()
      for (i=0; i<40; i++) {
        var el = ons.createElement(li_template.replaceAll('##index##', i).replaceAll('##address##', 0).replaceAll('##value##', 0))
        row_search_result_list.append(el)
      }
    };

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

    function setup_search_type(_shows, _hides) {
        sel_search_type.val(current_search_type)
        if (current_search_type === 'exact') {
            _shows.push(...[row_search_value])
            _hides.push(...[row_search_direction])
        } else {
            if (current_search_round > 0) {
                _shows.push(row_search_direction)
            } else {
                _hides.push(row_search_direction)
            }
            _hides.push(...[row_search_value])
        }
    }

    function setup_start_state() {
        var shows = [div_search_information_block]
        var hides = [div_search_results]
        setup_search_type(shows, hides)
        show(shows)
        hide(hides)
        if (current_process === "") {
            disable([btn_reset_button, btn_search_button, sel_search_size, sel_search_type, inp_search_value, sel_search_direction]);
        } else {
            disable([btn_reset_button]);
            enable([btn_search_button, sel_search_size, sel_search_type, inp_search_value, sel_search_direction]);
        }
    }

    function setup_searching_state(result = {'progress': 0}) {
        progress = result.progress
        var shows = [div_search_information_block, row_search_progress, div_search_results]
        var hides = [row_search_result_list]
        setup_search_type(shows, hides)
        show(shows)
        hide(hides)
        disable([btn_reset_button, btn_search_button, sel_search_size, sel_search_type, inp_search_value, sel_search_direction]);
        search_progress.text(progress+'%')
    }

    function setup_continue_state(result) {
        var shows = [div_search_information_block, div_search_results, row_search_result_list]
        var hides = [row_search_progress]
        var enables = [btn_reset_button, inp_search_value, sel_search_direction]
        var disables = [sel_search_type, sel_search_size]
        var last_search = result.last_search
        setup_search_type(shows, hides)
        if (last_search == 'UNKNOWN_INITIAL') {
            result_count.text('ready after next search')
            hides.push(result_count_disclaimer)
            enables.push(btn_search_button)
        } else {
            result_count.text(result.number_of_results)
            if (result.number_of_results > 40) {
                shows.push(result_count_disclaimer)
            } else {
                hides.push(result_count_disclaimer)
            }
            if (result.number_of_results == 0) {
                disables.push(btn_search_button)
            } else {
                enables.push(btn_search_button)
            }
        }
        enable(enables);
        disable(disables)
        show(shows);
        hide(hides);
        populate_results()
    }

    function on_search_status(result) {
        current_state = result.state || current_state
        current_search_type = result.search_type || current_search_type
        current_search_round = result.search_round || current_search_round
        current_search_results = result.search_results || current_search_results
        var repeat = result.repeat || 0
        var error = result.error || ""
        if (!initialized) {
            initialized = true
        }
        switch (result.state) {
            case 'SEARCH_STATE_START':
                setup_start_state()
                break;
            case 'SEARCH_STATE_SEARCHING':
                setup_searching_state(result)
                break;
            case 'SEARCH_STATE_CONTINUE':
                setup_continue_state(result)
                break;
        }
        if (repeat > 0) {
            setTimeout(function() {$.send('/search', { "command": "SEARCH_STATUS" }, on_search_status);}, repeat)
        }
        if (error.length > 0) {
            ons.notification.toast(error, { timeout: 5000, animation: 'fall' })
        }
    }

    function populate_results() {
        var elements = $(".result-row")
        for (i=0; i<40; i++) {
            var el = $(elements[i])
            if (i < current_search_results.length) {
                var item = current_search_results[i]
                var address_element = el.find(".address")
                var value_element = el.find(".value")
                var freeze_element = el.find(".freeze")
                if (value_element.is(":focus")) {
                    continue
                }
                address_element.text((item.address).toString(16).toUpperCase().padStart(16, '0'))
                value_element.attr('data-address', item.address)
                freeze_element.attr('data-address', item.address)
                value_element.val(item.value)
                el.show()
            } else {
                el.hide()
            }

        }
    }

    function initialize() {
        div_search_information_block = $("#search_information_block")
        sel_search_size = $("#search_size");
        sel_search_type = $("#search_type");
        row_search_value = $("#search_value_row");
        inp_search_value = $("#search_value");
        row_search_direction = $("#search_direction_row");
        sel_search_direction = $("#search_direction");
        btn_search_button = $("#search_button");
        btn_reset_button = $("#search_reset_button");
        div_search_results = $("#search_results");
        row_search_result_list = $("#search_result_list");
        result_count = $("#result_count")
        result_count_disclaimer = $("#result_count_disclaimer")
        row_search_progress = $("#search_progress_row")
        search_progress = $("#search_progress")

        $.send('/search', { "command": "SEARCH_INITIALIZE" }, on_search_status);
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

}( window.search = window.search || {}, jQuery ));
