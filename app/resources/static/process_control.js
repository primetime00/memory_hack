(function( process_control, $, undefined ) {
    //Private Property
    var process_map = {}
    var last_update_time = -1
    var request_id = 0
    var process_list = []


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

    function generate_process_list(new_list) {
        var same = process_list.filter(x => new_list.includes(x))
        var remove = process_list.filter(x => !new_list.includes(x))
        var add = new_list.filter(x => !process_list.includes(x))
        return {'add': add, 'remove': remove, 'processes': same.concat(add) }
    }

    function get_info() {
        $.post('/info', { "command": "GET_PROCESSES", 'id': request_id}, function(result)
        {
            request_id += 1
            if (result.hasOwnProperty('error')) {
                ons.notification.toast(result.error, { timeout: 4000, animation: 'fall' })
                return
            }
            if (result.hasOwnProperty('processes')) {
                var p_data = generate_process_list(result.processes)
                process_list = p_data.processes
                search.on_update_process_list(p_data.add, p_data.remove);
                codelist.on_update_process_list(p_data.add, p_data.remove);
                aob.on_update_process_list(p_data.add, p_data.remove);
            }
            for (const service of result.services) {
                if (service.name === 'search') {
                    search.on_update_selected_process(service.process);
                }
                else if (service.name === 'codelist') {
                    codelist.on_update_selected_process(service.process);
                }
                else if (service.name === 'aob') {
                    aob.on_update_selected_process(service.process);
                }
            }
        });
        setTimeout(get_info, 1000)
    };

}( window.process_control = window.process_control || {}, jQuery ));
