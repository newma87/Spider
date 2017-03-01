/*
Navicat MySQL Data Transfer

Source Server         : localhost
Source Server Version : 50625
Source Host           : localhost:3306
Source Database       : spider

Target Server Type    : MYSQL
Target Server Version : 50625
File Encoding         : 65001

Date: 2017-03-01 17:25:24
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for image
-- ----------------------------
DROP TABLE IF EXISTS `image`;
CREATE TABLE `image` (
  `id` int(255) unsigned NOT NULL AUTO_INCREMENT,
  `url` varchar(1024) CHARACTER SET ascii DEFAULT NULL,
  `request_state` tinyint(1) unsigned NOT NULL DEFAULT '0',
  `name` varchar(255) CHARACTER SET ascii DEFAULT NULL,
  `save_path` varchar(255) DEFAULT NULL,
  `from_website` int(255) unsigned NOT NULL DEFAULT '0',
  `last_modify` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT 'user id',
  `name` char(255) DEFAULT NULL COMMENT 'user name',
  `type` tinyint(1) DEFAULT '0' COMMENT 'user type',
  `comment` varchar(1024) DEFAULT NULL COMMENT 'user comment',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for website
-- ----------------------------
DROP TABLE IF EXISTS `website`;
CREATE TABLE `website` (
  `id` int(255) unsigned NOT NULL AUTO_INCREMENT,
  `url` varchar(1024) CHARACTER SET ascii DEFAULT NULL,
  `request_state` tinyint(1) unsigned NOT NULL DEFAULT '0',
  `from_url` int(255) unsigned NOT NULL DEFAULT '0',
  `last_modify` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
SET FOREIGN_KEY_CHECKS=1;
