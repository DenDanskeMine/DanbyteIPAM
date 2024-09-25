DROP TABLE IF EXISTS `SUBNETS`;
CREATE TABLE `SUBNETS`
(
    name          varchar(255) null,
    `range`       varchar(255) null comment 'IP RANGE',
    is_favorite   tinyint(1)   null comment 'Is teh subnet favorite?',
    is_nested     tinyint(1)   null comment 'is teh subnet nessted? - More sunbets under it',
    is_scannable  tinyint(1)   null,
    is_resolvable tinyint(1)   null,
    show_status   tinyint(1)   null,
    id            int auto_increment
        primary key
);

DROP TABLE IF EXISTS `SWITCHES`;
CREATE TABLE `SWITCHES`
(
    id               int auto_increment
        primary key,
    hostname         varchar(100)                           not null,
    ip_address       varchar(45)                            not null,
    location         varchar(255)                           null,
    community        varchar(100)                           null,
    is_favorite      tinyint(1) default 0                   null,
    model            varchar(100)                           null,
    firmware_version varchar(50)                            null,
    port_count       int                                    null,
    is_online        tinyint(1)                             null,
    created_at       timestamp  default current_timestamp() null,
    constraint hostname
        unique (hostname)
);

DROP TABLE IF EXISTS `IPs`;
CREATE TABLE `IPs`
(
    id            int auto_increment
        primary key,
    address       varchar(255)                             not null,
    subnet_id     int                                      not null,
    is_favorite   tinyint(1)   default 0                   null,
    is_nested     tinyint(1)   default 0                   null,
    is_scannable  tinyint(1)   default 0                   null,
    is_resolvable tinyint(1)   default 0                   null,
    show_status   tinyint(1)   default 0                   null,
    status        varchar(255) default '3'                 null,
    owner         varchar(255)                             null,
    is_gateway    tinyint(1)   default 0                   null,
    last_edited   timestamp    default current_timestamp() null on update current_timestamp(),
    last_seen     timestamp                                null,
    mac           varchar(255)                             null,
    description   text                                     null,
    note          text                                     null,
    switch        varchar(255)                             null,
    device        varchar(255)                             null,
    location      varchar(255)                             null,
    hostname      varchar(255)                             null,
    port          varchar(255)                             null,
    switch_id     int                                      null,
    constraint IPs_ibfk_1
        foreign key (subnet_id) references SUBNETS (id)
            on delete cascade,
    constraint fk_switch
        foreign key (switch_id) references SWITCHES (id)
            on delete cascade
);

CREATE INDEX subnet_id
    ON IPs (subnet_id);

DROP TABLE IF EXISTS `SNMP_DATA_SWITCH`;
CREATE TABLE `SNMP_DATA_SWITCH`
(
    id                        int auto_increment
        primary key,
    switch_id                 int                                   null,
    numOf_int                 int                                   not null,
    int_names                 text                                  not null,
    int_status                text                                  not null,
    is_shutdown               int(1)    default 0                   null,
    timestamp                 timestamp default current_timestamp() null,
    interface_shutdown_status text                                  not null,
    vlan                      text                                  null,
    mac                       varchar(4096)                         null,
    constraint SNMP_DATA_SWITCH_ibfk_1
        foreign key (switch_id) references SWITCHES (id)
            on delete cascade
);

CREATE INDEX switch_id
    ON SNMP_DATA_SWITCH (switch_id);

CREATE INDEX idx_switches_hostname
    ON SWITCHES (hostname);

CREATE INDEX idx_switches_ip_address
    ON SWITCHES (ip_address);

CREATE INDEX idx_switches_location
    ON SWITCHES (location);

DROP TABLE IF EXISTS `USERS`;
CREATE TABLE `USERS`
(
    id         int auto_increment
        primary key,
    username   varchar(50)                            not null,
    password   varchar(255)                           not null,
    name       varchar(50)                            not null,
    lastname   varchar(50)                            not null,
    ro         tinyint(1) default 0                   null,
    is_admin   tinyint(1) default 0                   null,
    created_at timestamp  default current_timestamp() null,
    constraint username
        unique (username)
);

DROP TABLE IF EXISTS `form_fields`;
CREATE TABLE `form_fields`
(
    id            int auto_increment
        primary key,
    field_name    varchar(255)         null,
    field_type    varchar(255)         null,
    is_dynamic    tinyint(1) default 1 null,
    display_order int                  null
);

DROP TABLE IF EXISTS `dynamic_values`;
CREATE TABLE `dynamic_values`
(
    id            int auto_increment
        primary key,
    ip_id         int  null,
    form_field_id int  null,
    field_value   text null,
    constraint dynamic_values_ibfk_1
        foreign key (ip_id) references IPs (id)
            on delete cascade,
    constraint dynamic_values_ibfk_2
        foreign key (form_field_id) references form_fields (id)
            on delete cascade
);

CREATE INDEX form_field_id
    ON dynamic_values (form_field_id);

CREATE INDEX ip_id
    ON dynamic_values (ip_id);