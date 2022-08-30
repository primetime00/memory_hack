(function( search, $, undefined ) {
    //Private Property
    var test = true;

    //Public Property
    search.test = "Bacon Strips";

    //Public Method
    search.search_changed = function(option) {
      if (option.value == 'unknown') {
        $('#search_direction_div').hide()
        $('#search_value_div').hide()
      } else {
        $('#search_direction_div').hide()
        $('#search_value_div').show()
      }
    };

    search.write_click = function(obj, index, address) {
      console.log(index, address)
      var value = $(`input[name="value_${index}"]`).val();
        $.ajax
        ({
            url: '/search',
            data: {"write": address, "value": value},
            type: 'post',
            success: function(result)
            {

            }
        });
    };

    search.change_found_value = function(txt, index) {
        $(`#write_button_${index}`).prop("disabled", txt.length == 0)
    }

    search.on_search_clicked = function() {
        var proc = $("select[class='process_control']").val();
        var size = $("#search_size").val();
        var type = $("#search_type").val();
        var value = $("#search_value").val();
        if (type == 'unknown') {
          value = $("#search_direction").val()
        }
        $("#search_button").prop("disabled",true);

        $("#search_value").prop("disabled",true);
        $("#search_reset_button").prop("disabled",true);

        $('#search_results').hide();
        $('#search_result_table').hide();
        $('#search_reset_button').prop("disabled",true);

        $.ajax
        ({
            url: '/search',
            data: {"process": proc, "size": size, "type": type, "value": value, "button": true},
            type: 'post',
            success: function(result)
            {
              setTimeout(get_status, 1000);
            }
        });
    };

    search.on_reset_clicked = function() {
        $("select[name='process']").prop("disabled",false);
        $("#search_size").prop("disabled",false);
        $("#search_type").prop("disabled",false);
        $('#search_searching').hide();
        $("#search_reset_button").prop("disabled",true);
        $.ajax
        ({
            url: '/search',
            data: {"reset": true},
            type: 'post',
            success: function(result)
            {
              setTimeout(get_status, 1000);
              $('#search_direction_div').hide()
              $('#search_results').hide();
              $('#search_searching').hide();
              $('#search_result_table').hide();
              $('#search_reset_button').prop("disabled",true);
              $('#search_button').prop("disabled",true);
            }
        });
    };

    search.on_process_changed = function(process) {
      search.on_reset_clicked();
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
    };

    //Private Methods
   function update_addresses() {
       $.ajax
        ({
            url: '/search',
            data: {"button": false, "update_address": true},
            type: 'post',
            success: function(result)
            {
              var status = result.status
              if (status == 'UPDATE_ADDRESSES') {
                if (result.addresses.length > 0) {
                  update_table(result.addresses);
                  setTimeout(update_addresses, 1000);
                }
              }
            }
        });
    };

    function action_status(result) {
      var status = result.status
      if (status == 'WAITING_START') {
        $("select[name='process']").prop("disabled",false);
        $("#search_size").prop("disabled",false);
        $("#search_type").prop("disabled",false);
        $("#search_value").prop("disabled",false);
        $("#search_reset_button").prop("disabled",true);

        $('#search_results').hide();
        $('#search_searching').hide();
        $('#search_result_table').hide();
        $('#search_reset_button').prop("disabled",true);
        $('#search_button').prop("disabled",false);
        $('#search_errors').hide();
      }
      else if (status == 'ERROR') {
        $("select[name='process']").prop("disabled",false);
        $("#search_size").prop("disabled",false);
        $("#search_type").prop("disabled",false);
        $("#search_value").prop("disabled",false);
        $("#search_reset_button").prop("disabled",true);

        $('#search_results').hide();
        $('#search_searching').hide();
        $('#search_result_table').hide();
        $('#search_reset_button').prop("disabled",true);
        $('#search_button').prop("disabled",false);
        $('#search_errors').text(result.error);
        $('#search_errors').show();
      }
      else if (status == 'SEARCHING') {
        setTimeout(get_status, 1000);
        $("select[name='process']").prop("disabled",true);
        $("#search_size").prop("disabled",true);
        $("#search_type").prop("disabled",true);
        $("#search_value").prop("disabled",true);
        $("#search_reset_button").prop("disabled",true);

        $('#search_searching').show();
        $('#search_progress').text(result.progress + '%')
        $('#search_results').hide();
        $('#search_result_table').hide();
        $('#search_reset_button').prop("disabled",true);
        $('#search_errors').hide();
      }
      else if (status == 'WAITING_CONTINUE') {
        $("select[name='process']").prop("disabled",true);
        $("#search_size").prop("disabled",true);
        $("#search_type").prop("disabled",true);
        $("#search_value").prop("disabled",false);
        $("#search_reset_button").prop("disabled",true);

        $('#search_reset_button').prop("disabled",false);
        $('#search_button').prop("disabled",false);
        $('#search_errors').hide();
        show_results(result)
      }
      if (result.process === "") {
        $('#search_reset_button').prop("disabled",true);
        $('#search_button').prop("disabled",true);
      }
    };

    function get_status() {
        $.ajax
        ({
            url: '/search',
            data: {"button": false},
            type: 'post',
            success: function(result)
            {
              action_status(result)
            }
        });
    };

    function show_results(res) {
      $('#search_searching').hide();
      if (res.type == 'unknown') {
        $('#search_value_div').hide()
        $('#search_direction_div').show()
        if (res.iteration >= 2) {
          $('#search_num_results').text(res.count)
          $('#search_results').show();
          if (res.count == 0) {
            $('#search_button').prop("disabled",true);
          }
        } else {
          $('#search_results').hide();
        }
      }
      else {
        $('#search_num_results').text(res.count)
        $('#search_results').show();
        if (res.count == 0) {
          $('#search_button').prop("disabled",true);
        }
      }
      $("#search_table_body").empty();
      if (res.addresses.length > 0) {
        create_table(res.addresses)
        $('#search_result_table').show();
        setTimeout(update_addresses, 1000);
      }
    };

    function create_table(addresses) {
      $("#search_table_body").empty();
      $.each(addresses, function( index, address ){
        $('#search_result_table').append(`<tr name="${address[0]}"><td>${address[0]}</td><td name="address_value">${address[1]}</td><td><input type="text" oninput="search.change_found_value(this.value, ${index})" name="value_${index}"></input></td><td><button disabled type="button" class="write-button" id="write_button_${index}" onclick="search.write_click(this, ${index}, ${address})">Write</button></td></tr>`);
      });
    };

    function update_table(addresses) {
     $.each(addresses, function( index, address ){
        var s = $("#search_result_table").find("tbody tr").eq(index).children().eq(1)
        s.text(address[1])
      });
    };

    function initialize() {
        $.ajax
        ({
            url: '/search',
            data: {"initialize": true},
            type: 'post',
            success: function(result)
            {
              on_ready(result)
            }
        });
    };

    function on_ready(data) {
      action_status(data)
      if (data.process) {
        $("select[class='process_control']").val(data.process);
      }
      if (data.type) {
        $("#search_type").val(data.type);
      }
      if (data.size) {
        $("#search_size").val(data.size);
      }
      if (data.type == 'unknown') {
        $('#search_value_div').hide()
        $('#search_direction_div').show()
        if (data.value) {
          $("#search_direction").val(data.value);
        }
      }
      else {
        $('#search_direction_div').hide()
        $('#search_value_div').show()
        if (data.value) {
          $("#search_value").val(data.value);
        }
      }
    };

}( window.search = window.search || {}, jQuery ));
