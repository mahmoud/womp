var DASH = (function ($) {
    var DASH = {
        articleLists: []
    };

    $(document).ready(function() {
        if ($('#autorefresh').is(':checked')) {
            DASH.start_reload();
        }

        $('#autorefresh').click(function() {
            if ($(this).is(':checked')){
                DASH.start_reload();
            }
            else {
                DASH.stop_reload();
            }
        });

        $('#add-new-list').click(function () {
            DASH.create_list_menu($(this));
        });

        $('.article-list-row').each(function () {
            DASH.articleLists.push(ArticleList.fromTableRow($(this)));
        });

        $('form#remove_articles').submit(function (e) {
            e.preventDefault();
            e.stopPropagation();

            var $this = $(this),
                opts = {type: $this.attr('method'), data: {}},
                $toRemove = $this.find('input.article-choice:checked');

            $toRemove.each(function () {
                var $check = $(this);
                opts.data[$check.attr('name')] = 'remove';
            });

            opts.success = function () {
                $toRemove.closest('.article_set_list').remove();
            };

            $.ajax($this.attr('action'), opts);
        });

        $('form#new_action').submit(function (e) {
            e.preventDefault();
            e.stopPropagation();

            var $this = $(this),
                opts = {type: $this.attr('method'), data: {}},
                $text = $this.find('textarea[name=articles]'),
                text = $text.val(),
                articles = text.split('\n'),
                existing = {};

            opts.data.articles = text;
            opts.data.meta = $this.find('textarea[name=meta]').text();
            if ( $this.find('input[name=resolve]').is('checked') ) {
                opts.data.resolve = 'True';
            }

            $('input.article-choice').each(function () {
                existing[$(this).attr('id')] = true;
            });

            opts.success = function () {
                $text.val('');

                var i, $li, $input, $label,
                    $list = $('form#remove_articles').find('ul');

                for (i = 0; i < articles.length; i++) {
                    if (existing[articles[i]] === true) {
                        continue;
                    }

                    $li = $('<li>', {'class': 'article_set_list'});
                    $input = $('<input>', {
                        'class': 'article-choice',
                        type: 'checkbox',
                        name: articles[i],
                        id: articles[i],
                        value: 'remove'
                    });
                    $label = $('<label>', {'for': articles[i]}).text(articles[i]);
                    $li.append(
                        $input,
                        ' ',
                        $label
                    );
                    $list.append($li);
                }
            };

            $.ajax($this.attr('action'), opts);
        });
    });


    DASH.ajax_refresh = function ajax_refresh(div_selector, url, repeat_delay) {
        div_selector = div_selector || '#content';
        url = url || document.URL;
        repeat_delay = repeat_delay || null;
        $(div_selector).load(document.URL + ' ' + div_selector, function(res, status, xhr) {
            if (status !== 'success') {
                DASH.stop_reload();
                $('#autorefresh').prop('checked', false);
            } else {
                if (repeat_delay) {
                    if ($('#autorefresh').is(':checked')){
                        DASH.reload = setTimeout(function() {
                            DASH.ajax_refresh(div_selector, url, repeat_delay);
                        }, repeat_delay);
                    } else {
                        // hmmm, sometimes it doesn't respond to my click... this should stop it
                        DASH.stop_reload();
                    }
                }
            }
        });
    };

    DASH.get_refresher = function get_refresher(div_selector, url, repeat_delay) {
        var do_refresh = function do_refresh() {
            return ajax_refresh(div_selector, url, repeat_delay);
        };
    };

    DASH.stop_reload = function stop_reload() {
        clearTimeout(DASH.reload);
    };

    DASH.start_reload = function start_reload(rate) {
        rate = rate || 221;
        DASH.ajax_refresh('', '', rate);
    };

    DASH.create_list_menu = function create_list_menu($link) {
        function destructMe() {
            $interface.remove();
        }

        function setErr(msg) {
            $interface.find( '.error' ).remove();
            $err = $('<span>', {'class': 'error'}).text(msg);
            $interface.append($err);
        }

        var $interface = $('<div>'),
            $field = $('<input>', {
                type: 'text',
                id: 'create-a-list',
                name: 'list_name'
            }),
            $button = $('<button>', {
                type: 'button',
                id: 'create-list-submit'
            }).text( 'Create!' ),
            $cancel = $('<button>', {
                type: 'cancel',
                id: 'create-list-cancel'
            }).text( 'Cancel' );

        $button.click(function () {
            if ($field.val() === '') {
                setErr('Please enter a list name.');
            } else {
                DASH.create_list($field.val(), destructMe, setErr );
            }
        });

        $cancel.click(destructMe);

        $interface.append(
            $field,
            $button,
            $cancel
        );

        $link.after($interface);
    };

    DASH.create_list = function create_list(name, cb, err) {
        $.ajax(
            '/list_create/' + name,
            {
                type: 'PUT',
                success: function (data) {
                    DASH.add_new_row(data);
                    cb();
                },

                // Yeah, status codes, they're awesome.
                statusCode: {
                    409: function () {
                        err('That list already exists, please choose a different name.');
                    },
                    400: function () {
                        err('Please enter a non-empty name with no period (.) characters.');
                    }
                }
            }
        );
    };

    DASH.add_new_row = function add_new_row(list) {
        var al = new ArticleList(list.name, list.articles, list.actions, list.date);
        al.buildInterface();
        al.attach($('#in-prog-table'));
        DASH.articleLists.push(al);
    };

    return DASH;
}(jQuery));
