# drop database if exists android_hot_fix;

#create database android_hot_fix;

use android_hot_fix;

grant select, insert, update, delete on android_hot_fix.* to 'root' identified by 'admin_zzc';

create table users (
    id varchar(50) not null,
    email varchar(50) not null,
    passwd varchar(50) not null,
    admin bool not null,
    name varchar(50) not null,
    image varchar(500) not null,
    create_at real not null,
    unique key idx_email (email),
    key idx_create_at (create_at),
    primary key (id)
) engine=innodb default charset=utf8;

CREATE TABLE `android_hot_fix`.`app` (
  `id` INT NOT NULL,
  `app_key` VARCHAR(50) NOT NULL,
  `app_name` VARCHAR(50) NOT NULL,
  `create_time` VARCHAR(50) NOT NULL,
  `app_type` INT NULL,
  `user_id` VARCHAR(50) NOT NULL,
  `app_icon` VARCHAR(500) NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `android_hot_fix`.`app_version` (
  `id` INT NOT NULL,
  `app_id` VARCHAR(50) NOT NULL,
  `version_code` VARCHAR(50) NOT NULL,
  `create_time` VARCHAR(50) NOT NULL,
  PRIMARY KEY (`id`)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `patch_record` (
  `id` int(11) NOT NULL,
  `app_version_code` varchar(45) NOT NULL COMMENT '应用版本号',
  `app_id` varchar(45) NOT NULL COMMENT '所属应用id',
  `patch_version_code` varchar(45) NOT NULL COMMENT '补丁包版本号',
  `update_time` varchar(45) NOT NULL COMMENT '更新时间',
  `patch_link` varchar(500) NOT NULL COMMENT '补丁包链接',
  `describe` text COMMENT '补丁描述',
  `patch_size` longblob NOT NULL,
  `is_effective` tinyint(4) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
