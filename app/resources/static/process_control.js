(function( process_control, $, undefined ) {
    //Private Property
    var process_map = {}
    var last_update_time = -1
    var request_id = 0


    //Public Property

    //Public Method
    process_control.ready = function() {
        on_ready();
    }

    process_control.get_process_list = function() {
        process_list = []
        for (var m in process_map) {
            process_list.push(process_map[m].name)
        }
        return process_list
    }

    process_control.request_process = function(process, service, ret_function) {
        $.send('/info', { "command": "REQUEST_PROCESS", 'process': process, 'service': service}, ret_function)
    }

    //Private Methods
    function on_ready() {
        get_info()
    };

    function get_info() {
        $.post('/info', { "command": "GET_PROCESSES", 'id': request_id}, function(result)
        {
            request_id += 1
            if (result.hasOwnProperty('set')) {
                search.on_update_process_list(result.set, []);
                aob.on_update_process_list(result.set, []);
            }
            else {
                if (result.add.length > 0 || result.remove.length > 0) {
                    search.on_update_process_list(result.add, result.remove);
                    aob.on_update_process_list(result.add, result.remove);
                }
            }
            for (const service of result.services) {
                if (service.name === 'search') {
                    search.on_update_selected_process(service.process);
                }
                else if (service.name === 'aob') {
                    aob.on_update_selected_process(service.process);
                }
            }
        });
        setTimeout(get_info, 1000)
    };

}( window.process_control = window.process_control || {}, jQuery ));
