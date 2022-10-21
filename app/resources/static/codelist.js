(function( codelist, $, undefined ) {
    //Private Property
    var sel_codelist_process;
    var div_codelist_block;
    var row_codelist_loadsave;
    var sel_codelist_file;
    var btn_add_code;
    var btn_paste_code;

    var code_list;
    var code_data;
    var aob_resolve_map = {}
    var value_map = {}

    //Public Method
    codelist.on_process_changed = function(process) {
        process_control.request_process(process, 'codelist', function(result){
            if (!result.success) {
                set_process('_null')
                ons.notification.toast(result.error, { timeout: 4000, animation: 'fall' })
            } else {
                set_process(process)
            }
        })
    };

    codelist.on_update_process_list = function(process_list_add, process_list_remove) {
        var options = sel_codelist_process.children('option') ;
        var selected = sel_codelist_process.find('option:selected')
        if (process_list_remove.includes(selected.val())) {
            div_codelist_block.hide()
        }
        for (var i=options.length-1; i>=0; i--) {
            var option=options[i]
            if (process_list_remove.includes(option.value)) {
                option.remove()
            }
        }
        var f = sel_codelist_process.find('option:first')
        for (const item of process_list_add) {
            f.after($('<option>', {value: item, text: item}))
        }
    }

    codelist.on_update_selected_process = function(process_name) {
        var value = sel_codelist_process.val()
        if (value != process_name){
            set_process(process_name)
        }
    }

    codelist.ready = function()  {
        sel_codelist_process = $("#codelist_process");
        div_codelist_block = $("#codelist_block");
        btn_add_code = $("#add_new_code_button");
        btn_add_code[0].hide()
        btn_paste_code = $("#paste_new_code_button");
        btn_paste_code[0].hide()
        row_codelist_loadsave = $("#row_codelist_loadsave");
        sel_codelist_file = $("#codelist_file_selection")
        component_list.forEach(item => {
            item['obj'] = $("#"+item.id)
            if (has(item, 'changed')) {
                item.obj.bind('change', {item: item}, (event) => event.data.item.changed(event.data.item))
            }
        })

    };

    codelist.code_value_changed = function(did_blur, ele, index) {
        if (!did_blur) {
            if(event.key === 'Enter' || event.key === 'Return'  || event.keyCode == 13) {
                ele.blur()
            }
        } else {
            $.send('/codelist', {'command': 'CODELIST_WRITE', 'index': index, 'value': ele.value}, on_codelist_status)
        }
    }

    codelist.code_name_changed = function(did_blur, ele, index) {
        if (!did_blur) {
            if(event.key === 'Enter' || event.key === 'Return'  || event.keyCode === 13) {
                ele.blur()
            }
        }
        else {
            $.send('/codelist', {'command': 'CODELIST_NAME', 'index': index, 'name': ele.value}, on_codelist_status)
        }
    }

    codelist.code_size_changed = function(ele, index) {
        $.send('/codelist', { 'command': "CODELIST_SIZE", 'index': index, 'size': ele.value}, on_codelist_status);
    }

    codelist.code_freeze_changed = function(ele, index) {
        $.send('/codelist', { 'command': "CODELIST_FREEZE", 'index': index, 'freeze': ele.checked}, on_codelist_status);
    }

    codelist.on_refresh = function(element, index) {
        $.send('/codelist', { 'command': "CODELIST_REFRESH", 'index': index}, on_codelist_status);
    }


    codelist.code_menu_clicked = function(ele, index) {
        ons.createElement('code_menu', { append: true }).then(function(popover) {

            items = $(popover).find('ons-list-item')
            for (i=0; i<items.length; i++) {
                var item = items[i]
                if (item.getAttribute("name") === 'copy_clipboard' && document.clipboard.has_address() && aob_resolve_map.hasOwnProperty(index) && aob_resolve_map[index].length > 0) {
                    $(item).removeClass('hidden')
                }
                $(item).bind('click', {list_id: item.getAttribute("name"), code_index: index}, (event) => {codelist.option_clicked(event.data.list_id, event.data.code_index); popover.hide()})
            }
            popover.show("#"+ele.id);
        });
    }

    codelist.option_clicked = function(list_id, code_index) {
        switch (list_id) {
            case 'edit':
                var source = code_data[code_index]['Source']
                var dt = {'title': 'Edit Code', 'index': code_index}
                if (source === 'address') {
                    dt['address'] = code_data[code_index]['Address'].toString(16).toUpperCase()
                } else {
                    dt['aob'] = code_data[code_index]['AOB']
                    dt['offset'] = code_data[code_index]['Offset']
                }
                component_code_dialog.create(dt)
               break
            case 'copy':
                var source = code_data[code_index]['Source']
                var dt = {'title': 'Copy Code'}
                if (source === 'address') {
                    dt['address'] = code_data[code_index]['Address'].toString(16).toUpperCase()
                } else {
                    dt['aob'] = code_data[code_index]['AOB']
                    dt['offset'] = code_data[code_index]['Offset']
                }
                component_code_dialog.create(dt)
               break
            case 'delete':
                $.send('/codelist', { 'command': "CODELIST_DELETE_CODE", 'index': code_index}, on_codelist_status);
                break
            case 'copy_clipboard':
                var new_address = document.clipboard.data.address
                var offset = parseInt(code_data[code_index].Offset, 16)
                var resolved = aob_resolve_map[code_index][0] - offset
                var new_offset = new_address - resolved
                var cmd = { 'command': "CODELIST_ADD_CODE", 'type': 'aob',
                              'address': 0,
                              'aob': code_data[code_index].AOB,
                              'offset': new_offset.toString(16) }

                $.send('/codelist', cmd, on_codelist_status);
                break
        }
    }

    codelist.on_save_clicked = function(ele) {
        ons.createElement('code_save', { append: true }).then(function(popover) {
            var fname = component_codelist_file.file === '_null' ? '' : component_codelist_file.file
            $(popover).find('input[name="save_file"]').val(fname)
            $(popover).find('input[name="save_file"]').bind('input', (event) => {
                if (event.target.value.length > 0) {
                    $(popover).find('ons-button[name="save_button"]').removeAttr('disabled')
                } else {
                    $(popover).find('ons-button[name="save_button"]').attr('disabled', 'disabled')
                }
            })
            $(popover).find('ons-button[name="cancel_button"]').bind('click', (event) => {popover.hide()})

            if (fname.length == 0) {
                $(popover).find('ons-button[name="save_button"]').attr('disabled', 'disabled')
            }
            $(popover).find('ons-button[name="save_button"]').bind('click', (event) => {
                var file = $(popover).find('input[name="save_file"]').val()
                $.send('/codelist', { 'command': "CODELIST_SAVE", 'file': file}, on_codelist_status);
                popover.hide()
            })


            popover.show("#"+"codelist_save_button");
        });
    }

    codelist.on_delete_clicked = function(ele) {
        ons.createElement('delete_code_file', { append: true }).then(function(dialog) {
            $(dialog).find('#delete_code_file_name').text(component_codelist_file.file)
            $(dialog).find('ons-alert-dialog-button[name="cancel_button"]').bind('click', () => {dialog.hide()})
            $(dialog).find('ons-alert-dialog-button[name="delete_button"]').bind('click', () => {
                $.send('/codelist', { 'command': "CODELIST_DELETE_LIST", 'file': component_codelist_file.file}, on_codelist_status);
                dialog.hide()
            })
            dialog.show();
        });
    }

    codelist.on_add_clicked = function(ele) {
        component_code_dialog.create({})
    }

    codelist.get_dialog = function() {
        return component_code_dialog
    }

    codelist.address_copy = function(index) {
        var source = code_data[index]['Source']
        if (source === 'address') {
            document.clipboard.copy({'address': code_data[index]['Address'], 'value': value_map[index]})
        } else {
            document.clipboard.copy({'address': aob_resolve_map[index][0], 'value': value_map[index]})
        }
    }

    codelist.clipboard_data_copied = function(data) {
        btn_paste_code[0].show()
    }

    codelist.clipboard_data_pasted = function(data) {
        var cmd = { 'command': "CODELIST_ADD_CODE", 'type': has(data, 'address') ? 'address' : 'aob',
                              'address': has(data, 'address') ? parseInt(data.address).toString(16) : 0,
                              'aob': has(data, 'aob') ? data.aob : 0,
                              'offset': has(data, 'offset') ? data.offset : 0 }

        $.send('/codelist', cmd, on_codelist_status);
    }

    codelist.clipboard_data_cleared = function() {
        btn_paste_code[0].hide()

    }


    //Private Methods
    function on_codelist_ready() {
        $.send('/codelist', { 'command': "CODELIST_GET"}, on_codelist_status);
    }

    function on_codelist_status(result) {
        if (has(result, 'file_data')) {
            code_data = result.file_data
            component_code_list.empty()
            if (result.file_data === null) {
                code_list = undefined
                code_data = []
            } else {
                code_list = component_code_list
                code_list.setup(result, code_list)
                code_list.obj = $('#code_list')
            }
        } else if (code_list !== undefined) {
            code_list.setup(result, code_list)
        }
        component_codelist_file_row.setup(result, component_codelist_file_row)

        if (has(result, 'error')) {
            ons.notification.toast(result.error, { timeout: 4000, animation: 'fall' })
        }
        if (has(result, 'repeat') && result.repeat > 0) {
            setTimeout(()=>{$.send('/codelist', { "command": "CODELIST_STATUS" }, on_codelist_status);}, result.repeat)
        }
    }

    var component_codelist_file_row = {
        'id': "row_codelist_loadsave",
        'obj': undefined,
        'setup': (result, _this) => {
            if (component_codelist_file.obj === undefined) {
                component_codelist_file.obj = $('#'+component_codelist_file.id)
            }
            if (component_codelist_save.obj === undefined) {
                component_codelist_save.obj = $('#'+component_codelist_save.id)
            }
            if (component_codelist_delete.obj === undefined) {
                component_codelist_delete.obj = $('#'+component_codelist_delete.id)
            }
            component_codelist_file.setup(result, component_codelist_file)
            component_codelist_save.setup(result, component_codelist_save)
            component_codelist_delete.setup(result, component_codelist_delete)
        },
        'update': (_this) => {}
    }

    var component_codelist_save = {
        'id': "codelist_save_button",
        'obj': undefined,
        'setup': (result, _this) => {
            if (code_list && code_list.items.length > 0) {
                _this.obj.removeAttr('disabled')
            } else {
                _this.obj.attr('disabled', 'disabled')
            }
        },
        'update': (_this) => {}
    }

    var component_codelist_delete = {
        'id': "codelist_delete_button",
        'obj': undefined,
        'setup': (result, _this) => {
            if (code_list && code_list.items.length > 0 && component_codelist_file.file !== '_null') {
                _this.obj.removeAttr('disabled')
            } else {
                _this.obj.attr('disabled', 'disabled')
            }
        },
        'update': (_this) => {}
    }

    var component_codelist_file = {
        'id': "codelist_file_selection",
        'obj': undefined,
        'setup': (result, _this) => {
            if (has(result, 'files')) {
                _this['files'] = result.files;
                _this.obj.find('option[value != "_null"]').remove();
                _this.files.forEach((item, index) => {
                    _this.obj.find('option:first').after($('<option>', {value: item, text: item}))
                });
            }
            if (has(result, 'file')) {
                _this['file'] = result.file;
                _this.obj.val(_this['file'])
            }
        },
        'changed': (_this) => {
            $.send('/codelist', { "command": "CODELIST_LOAD", 'file': _this.obj.val() }, on_codelist_status);
            _this.update(_this)
        },
        'in': (name) => {return _this.files.includes(name);},
        'files': [],
        'file': "_null",
        'update': (_this) => {
        }
    }



    var component_code_list = {
        'id': "code_list",
        'obj': undefined,
        'setup': (result, _this) => {
            if (has(result, 'file_data')) {
                _this.items = []
                result.file_data.forEach((item, index) => {
                    var head = component_code_header.create(index, result.file_data[index])
                    var comp = component_code.create(index, result.file_data[index])
                    _this.items.push({'header':head, 'item': comp});
                    _this.obj.append(head.obj)
                    _this.obj.append(comp.obj)
                });
                result.file_data.forEach((res, index) => {
                    _this.items[index].header.setup(res, _this.items[index].header)
                    _this.items[index].item.setup(res, _this.items[index].item)
                });
            }
            if (has(result, 'results')) {
                aob_resolve_map = {}
                value_map = {}
                result.results.forEach((res, index) => {
                    _this.items[index].header.setup(res, _this.items[index].header)
                    _this.items[index].item.setup(res, _this.items[index].item)
                });
            }
        },
        'update': (_this) => {console.log('i update')},
        'template': '<ons-list id="code_list">##code_components##</ons-list>',
        'items-html': (_this) => {
            var html = ''
            _this.items.forEach((item, index) => {
                html+=item.template;
            });
            return html;
        },
        'empty': () => {
            $('#code_list').empty()
            component_code_list.obj = $('#code_list')
            while (component_code_list.items.length) { component_code_list.items.pop(); }
        },
        'items': []
    }

    var component_code_header = {
        'id': 'code_header_',
        'obj': undefined,
        'index': -1,
        'name_component': {},
        'setup': (result, _this) => {
            _this.rows.forEach( (item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {console.log('code item update')},
        'template': '<ons-list-header id="##id##" style="background-color:#ddd;"></ons-list-header>',
        'create': (index, data) => {
            var t = {...component_code_header};
            t.id = component_code_header.id+index
            t.index = index
            t.template = component_code_header.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            //create the elements
            t.rows = []
            t.rows.push(component_row_name.create(index))
            t.rows.forEach((item, index) =>{
                t.obj.append(item.obj)
            })
            return t;
        },
        'rows': []
    }

    var component_code = {
        'id': 'code_item_',
        'obj': undefined,
        'index': -1,
        'name_component': {},
        'setup': (result, _this) => {
            _this.rows.forEach( (item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {console.log('code item update')},
        'template': '<ons-list-item id="##id##" modifier="longdivider"></ons-list-item>',
        'create': (index, data) => {
            var t = {...component_code};
            t.id = component_code.id+index
            t.index = index
            t.template = component_code.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            //create the elements
            t.rows = []
            t.rows.push(component_row_value.create(index))
            if (data.Source == 'address') {
                t.rows.push(component_row_address.create(index))
            } else {
                t.rows.push(component_row_aob.create(index))
                t.rows.push(component_row_offset.create(index))
            }
            t.rows.forEach((item, index) =>{
                t.obj.append(item.obj)
            })
            return t;
        },
        'rows': []
    }

    var component_row_name = {
        'id': 'row_name_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.items.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {console.log('code name update')},
        'template': `<ons-row id="##id##" style="margin-bottom:10px; margin-top:0px;">
                        <ons-col align="center" width="75%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col align="center" width="10%" class="col ons-col-inner">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_name};
            t.id = component_row_name.id+index
            t.index = index
            t.template = component_row_name.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_name = component_code_name.create(index)
            t.obj.find('ons-col').eq(0).append(cc_name.obj)
            var cc_options = component_code_options.create(index)
            t.obj.find('ons-col').eq(1).append(cc_options.obj)
            t.items = [cc_name, cc_options]
            return t;
        },
        'items': []
    }
    var component_code_name = {
        'id': 'code_component_name_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Name')) {
                _this.obj.val(result.Name)
            }
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full" onkeydown="codelist.code_name_changed(false, this, ##index##)" onblur="codelist.code_name_changed(true, this, ##index##)" value="Name" autocomplete="chrome-off" autocapitalize="off" style="font-weight: bold;">',
        'create': index => {
            var t = {...component_code_name};
            t.id = component_code_name.id+index
            t.index = index
            t.template = component_code_name.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }
    var component_code_options = {
        'id': 'code_menu_button_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<button class="tp" onclick="codelist.code_menu_clicked(this, ##index##)" id="##id##"><div class="navigation"></div>',
        'create': index => {
            var t = {...component_code_options};
            t.id = component_code_options.id+index
            t.index = index
            t.template = component_code_options.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_value = {
        'id': 'row_value_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.items.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {console.log('code name update')},
        'template': `<ons-row id="##id##">
                        <ons-col align="center" width="25%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col align="center" width="55%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col align="right" width="15%" class="col ons-col-inner">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_value};
            t.id = component_row_value.id+index
            t.index = index
            t.template = component_row_value.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_size = component_code_size.create(index)
            t.obj.find('ons-col').eq(0).append(cc_size.obj)
            var cc_value = component_code_value.create(index)
            t.obj.find('ons-col').eq(1).append(cc_value.obj)
            var cc_freeze = component_code_freeze.create(index)
            t.obj.find('ons-col').eq(2).append(cc_freeze.obj)
            t.items = [cc_size, cc_value, cc_freeze]
            return t;
        },
        'items': []
    }
    var component_code_size = {
        'id': 'code_component_size_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Type')) {
                _this.obj.val(result.Type)
            }
        },
        'update': (_this) => {console.log('code name update')},
        'template': `<select name="code_size" id="##id##" class="select-input select-input--material" onchange="codelist.code_size_changed(this, ##index##)">
                        <option value="byte_1">BYTE</option>
                        <option value="byte_2">2 BYTES</option>
                        <option value="byte_4" selected>4 BYTES</option>
                        <option value="float">FLOAT</option>
                     </select>`,
        'create': index => {
            var t = {...component_code_size};
            t.id = component_code_size.id+index
            t.index = index
            t.template = component_code_size.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }
    var component_code_value = {
        'id': 'code_component_value_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Value')) {
                value_map[_this.index] = result.Value
                if ($(":focus")[0] && $(":focus")[0].id === _this.obj[0].id){
                    return
                }
                _this.obj.val(result.Value)
                if (result.Value == '??') {
                    _this.obj.attr('disabled', 'disabled')
                } else {
                    _this.obj.removeAttr('disabled')
                }
            }
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<input tabIndex="-1" inputmode="decimal" autocomplete="chrome-off" type="text" id="##id##" name="code_value" class="text-input text-input--material text-full r-value" onkeydown="codelist.code_value_changed(false, this, ##index##)" onblur="codelist.code_value_changed(true, this, ##index##)">',
        'create': index => {
            var t = {...component_code_value};
            t.id = component_code_value.id+index
            t.index = index
            t.template = component_code_value.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }
    var component_code_freeze = {
        'id': 'code_component_freeze_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Freeze')) {
                _this.obj.parent().find('input').prop("checked", result.Freeze)
            }
            if (has(result, 'Value')) {
                if (result.Value == '??' && !_this.obj.parent().find('input').prop("checked")) {
                    _this.obj.parent().find('input').attr('disabled', 'disabled')
                } else if (result.Value != '??' && _this.obj.parent().find('input').prop('disabled')) {
                    _this.obj.parent().find('input').removeAttr('disabled')
                }

            }

        },
        'update': (_this) => {console.log('code name update')},
        'template': '<label class="checkbox checkbox--material"><input tabIndex="-1" id="##id##" type="checkbox" class="checkbox__input checkbox--material__input" onchange="codelist.code_freeze_changed(this, ##index##)"> <div class="checkbox__checkmark checkbox--material__checkmark"></div>',
        'create': index => {
            var t = {...component_code_freeze};
            t.id = component_code_freeze.id+index
            t.index = index
            t.template = component_code_freeze.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_address = {
        'id': 'row_address_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.items.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {console.log('code name update')},
        'template': `<ons-row id="##id##">
                        <ons-col align="center" width="20%" class="col ons-col-inner">
                            Address:
                        </ons-col>
                        <ons-col align="center" width="60%" class="col ons-col-inner">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_address};
            t.id = component_row_address.id+index
            t.index = index
            t.template = component_row_address.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_address = component_code_address.create(index)
            t.obj.find('ons-col').eq(1).append(cc_address.obj)
            t.items = [cc_address]
            return t;
        },
        'items': []
    }
    var component_code_address = {
        'id': 'code_component_address_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Address')) {
                _this.obj.val(result.Address.toString(16).toUpperCase())
            }
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full r-value" oninput="codelist.address_value_changed(this)" readonly>',
        'create': index => {
            var t = {...component_code_address};
            t.id = component_code_address.id+index
            t.index = index
            t.template = component_code_address.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_aob = {
        'id': 'row_aob_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.items.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {console.log('code name update')},
        'template': `<ons-row id="##id##">
                        <ons-col align="center" width="20%" class="col ons-col-inner">
                            AOB:
                        </ons-col>
                        <ons-col align="center" width="60%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col align="center" width="20%" class="col ons-col-inner">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_aob};
            t.id = component_row_aob.id+index
            t.index = index
            t.template = component_row_aob.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_aob = component_code_aob.create(index)
            t.obj.find('ons-col').eq(1).append(cc_aob.obj)
            var cc_copy = component_copy.create(index)
            t.obj.find('ons-col').eq(2).append(cc_copy.obj)
            t.items = [cc_aob, cc_copy]
            return t;
        },
        'items': []
    }
    var component_code_aob = {
        'id': 'code_component_aob_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'AOB')) {
                _this.obj.val(result.AOB)
            }
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full r-value" oninput="codelist.aob_value_changed(this)" readonly>',
        'create': index => {
            var t = {...component_code_aob};
            t.id = component_code_aob.id+index
            t.index = index
            t.template = component_code_aob.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_copy = {
        'id': 'code_component_copy_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, "Addresses") && result.Addresses !== null && result.Addresses.length > 0) {
                _this.obj.show()
            } else {
                _this.obj.hide()
            }
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<ons-button id="##id##" modifier="material--flat" onclick="codelist.address_copy(##index##)"><ons-icon style="color:#777;" size="26px" icon="md-copy"></ons-icon></ons-button>',
        'create': index => {
            var t = {...component_copy};
            t.id = component_copy.id+index
            t.index = index
            t.template = component_copy.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_offset = {
        'id': 'row_offset_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.items.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {console.log('code name update')},
        'template': `<ons-row id="##id##">
                        <ons-col align="center" width="20%" class="col ons-col-inner">
                            Offset:
                        </ons-col>
                        <ons-col align="center" width="25%" class="col ons-col-inner" name="offset_refresh">
                            <ons-row>
                                <ons-col align="center" class="col ons-col-inner" name="first">
                                </ons-col>
                            </ons-row>
                            <ons-row>
                                <ons-col align="center" class="col ons-col-inner" name="second">
                                </ons-col>
                            </ons-row>
                        </ons-col>
                        <ons-col align="center" width="55%" class="col ons-col-inner" name="addresses">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_offset};
            t.id = component_row_offset.id+index
            t.index = index
            t.template = component_row_offset.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_offset = component_code_offset.create(index)
            var cc_offset_address = component_code_offset_address.create(index)
            var cc_offset_refresh = component_code_offset_refresh.create(index)

            t.obj.find('ons-col[name="offset_refresh"]').find('ons-col').eq(0).append(cc_offset.obj)
            t.obj.find('ons-col[name="offset_refresh"]').find('ons-col').eq(1).append(cc_offset_refresh.obj)
            t.obj.find('ons-col[name="addresses"]').append(cc_offset_address.obj)

            t.items = [cc_offset, cc_offset_address, cc_offset_refresh]
            return t;
        },
        'items': []
    }
    var component_code_offset = {
        'id': 'code_component_offset_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Offset')) {
                _this.obj.val(result.Offset)
            }
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full" oninput="codelist.offset_value_changed(this)" readonly>',
        'create': index => {
            var t = {...component_code_offset};
            t.id = component_code_offset.id+index
            t.index = index
            t.template = component_code_offset.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }
    var component_code_offset_address = {
        'id': 'code_component_offset_addresses_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Addresses')) {
                aob_resolve_map[_this.index] = []
                    if (result.Addresses != null) {
                    aob_resolve_map[_this.index] = result.Addresses
                    if ($(":focus")[0] && $(":focus")[0].id === _this.obj[0].id){
                        return
                    }
                    _this.obj.val("")
                    var addrs = ""
                    result.Addresses.forEach((item, index) =>{
                        addrs += item.toString(16).toUpperCase()
                        if (index < result.Addresses.length-1){
                            addrs+='\n'
                        }
                    })
                    _this.obj.val(addrs)
                }
            }
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<textarea id=##id## class="textarea" rows="3" placeholder="None found" readonly></textarea>',
        'create': index => {
            var t = {...component_code_offset_address};
            t.id = component_code_offset_address.id+index
            t.index = index
            t.template = component_code_offset_address.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }
    var component_code_offset_refresh = {
        'id': 'code_component_offset_refresh_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
        },
        'update': (_this) => {console.log('code name update')},
        'template': '<ons-button modifier="quiet" id="##id##" onclick="codelist.on_refresh(this, ##index##)">Refresh</ons-button>',
        'create': index => {
            var t = {...component_code_offset_refresh};
            t.id = component_code_offset_refresh.id+index
            t.index = index
            t.template = component_code_offset_refresh.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_code_dialog = {
        'id': 'add_code_dialog',
        'obj': undefined,
        'setup': (result, _this) => {
        },
        'update': (_this) => {console.log('code name update')},
        'setup': (data) => {
            if (has(data, 'title')) {
                component_code_dialog.obj.find('p').text(data.title)
            } else {
                component_code_dialog.obj.find('p').text('Add Code')
            }
            if (has(data, 'index')) {
                component_code_dialog.index = data.index
                $("#add_code_button").text('Ok')
            } else {
                component_code_dialog.index = -1
                $("#add_code_button").text('Add')
            }
            $("#add_code_address").val('')
            $("#add_code_aob").val('')
            $("#add_code_offset").val('')
            if (has(data, 'address')) {
                $("#add_code_type").val('address')
                $("#add_code_address").val(data.address)
                $("#add_code_address").parents("ons-row").show()
                $("#add_code_aob").parents("ons-row").hide()
                $("#add_code_offset").parents("ons-row").hide()
            } else if (has(data, 'aob')) {
                $("#add_code_type").val('aob')
                $("#add_code_aob").val(data.aob)
                $("#add_code_offset").val(data.offset)
                $("#add_code_address").parents("ons-row").hide()
                $("#add_code_aob").parents("ons-row").show()
                $("#add_code_offset").parents("ons-row").show()
            } else {
                $("#add_code_type").val('address')
                $("#add_code_aob").parents("ons-row").hide()
                $("#add_code_offset").parents("ons-row").hide()
                $("#add_code_address").parents("ons-row").show()
            }
            component_code_dialog.validate()
        },
        'create': (data) => {
            if (component_code_dialog.obj === undefined) {
                ons.createElement('add_code', { append: true })
                .then(function(dialog) {
                    component_code_dialog.obj = $(dialog)
                    component_code_dialog.setup(data)
                    dialog.show();
                });
            } else {
                component_code_dialog.setup(data)
                component_code_dialog.obj[0].show()
            }
        },
        'type_changed': () => {
            if ($("#add_code_type").val() === 'address') {
                $("#add_code_aob").parents("ons-row").hide()
                $("#add_code_offset").parents("ons-row").hide()
                $("#add_code_address").parents("ons-row").show()
            } else {
                $("#add_code_address").parents("ons-row").hide()
                $("#add_code_aob").parents("ons-row").show()
                $("#add_code_offset").parents("ons-row").show()
            }
            component_code_dialog.validate()
        },
        'index': -1,
        'validate': () => {
            if ($("#add_code_type").val() === 'address') {
                var addr = $("#add_code_address").val()
                if (/^[0-9A-F]{5,16}$/i.test(addr)) {
                    $("#add_code_button").removeAttr('disabled')
                } else {
                    $("#add_code_button").attr('disabled', 'disabled')
                }
            } else {
                var aob = $("#add_code_aob").val()
                var offset = $("#add_code_offset").val()
                if (/^(?:([0-9A-F]{2}|\?{2}) )*([0-9A-F]{2}|\?{2})$/i.test(aob) && /^-?[0-9A-F]{1,12}$/i.test(offset)) {
                    $("#add_code_button").removeAttr('disabled')
                } else {
                    $("#add_code_button").attr('disabled', 'disabled')
                }
            }
        },
        'on_cancel': () => {
            component_code_dialog.obj[0].hide()
        },
        'on_add': () => {
            var cmd = { 'command': "CODELIST_ADD_CODE", 'type': $("#add_code_type").val(),
                                  'address': $("#add_code_address").val(), 'aob': $("#add_code_aob").val(),
                                  'offset': $("#add_code_offset").val() }
            if (component_code_dialog.index >= 0) {
                cmd['index'] = component_code_dialog.index
            }

            $.send('/codelist', cmd, on_codelist_status);
            component_code_dialog.obj[0].hide()
        }
    }


    var component_list = [component_codelist_file, component_codelist_save, component_codelist_delete, component_code_list]

    function set_process(process_name) {
        sel_codelist_process.val(process_name)
        if (process_name === '_null') {
            process_name = ''
        }
        btn_add_code.removeClass('hide-fab')
        btn_paste_code.removeClass('hide-fab')
        if (process_name.length > 0) {
            div_codelist_block.show()
            btn_add_code[0].show()
            on_codelist_ready()
        } else {
            div_codelist_block.hide()
            btn_add_code[0].hide()
        }
        component_code_list.empty()
    }

    function update() {
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

}( window.codelist = window.codelist || {}, jQuery ));
