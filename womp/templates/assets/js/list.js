function ArticleList(name, articles, actions, date) {
    this.name = name;
    this.articles = articles;
    this.actions = actions;
    this.date = date;
}

ArticleList.fromTableRow = function ($row) {
    var name = $row.attr('data-list-name'),
        articles = $row.find('.articles-unresolved').text() - 0,
        actions = $row.find('.actions').text() - 0,
        date = $row.find('.date').text(),
        list = new ArticleList(name, articles, actions, date);

    list.$row = $row;
    list.$gather = $row.find('.gather-link');
    list.$delete = $row.find('.delete-link');

    list.registerEvents();

    return list;
};

var ALP = ArticleList.prototype;

ALP.buildInterface = function () {
    var $row = $('<tr>', {'class': 'article-list-row'});
        $namecell = $('<td>'),
        $name = $('<a>', {href: '/list_editor/' + this.name}).text(this.name),
        $articles = $('<td>').text(this.articles),
        $actions = $('<td>').text(this.actions),
        $date = $('<td>').text(this.date),
        $commands = $('<td>', {'class': 'controls'}),
        $gather = $('<a>', {'class': 'gather-link', href: '#'}).text('Gather data'),
        $delete = $('<a>', {'class': 'delete-link', href: '#'}).text('Delete');

    $commands.append(
        $gather,
        $('<br>'),
        $delete
    );

    $namecell.html($name);

    $row.append(
        $namecell,
        $articles,
        $actions,
        $date,
        $commands
    );

    this.$row = $row;
    this.$gather = $gather;
    this.$delete = $delete;

    this.registerEvents();
};

ALP.registerEvents = function () {
    this.$gather.click(this.gather.bind(this));
    this.$delete.click(this.remove.bind(this));
};

ALP.attach = function ($table) {
    $table.append(this.$row);
};

ALP.remove = function () {
    var $row = this.$row;

    $.getJSON('/list_delete/' + this.name, function (data) {
        if (data.success === true) {
            $row.remove();
        }
    });
};

ALP.gather = function () {
    var $row = this.$row;

    $.getJSON('/start_fetch/' + this.name, function (data) {
        if (data.status === 'running') {
            $row.find('.controls')
                .append('<br/><a href="' + data.url + '" target="_blank">View dashboard</a>');
            $.getJSON(data.url + '/json', function (data) {
                console.log(data);
            });
        } else {
            console.log('Current status: ' + data.status);
        }
    });
};
