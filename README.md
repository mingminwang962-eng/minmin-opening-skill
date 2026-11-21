# 开头skill

给出正文，获得3个完整口播开头和1个极简短版，并接回正文。

**版本：6.9.2** · 面向支持Skill的AI助手。

- 安装说明：https://tools.minmin11538.cn/opening/
- 官方版本清单：https://tools.minmin11538.cn/opening/release.json
- 完整包优先从敏敏下载站获取，不依赖GitHub下载。

## 怎么用

安装完整的「开头skill」目录，必要时重开对话。发送：

> 用开头skill，为下面这篇稿子写开头，给我3个完整版本和1个极简短版：……

八种切入方向，从正文中提取真实材料，搭建口播开头，核对正文第一句。实际效果取决于原稿、模型与修改判断，不承诺播放量或爆款。

## 使用时检查更新

每个安装版本24小时内最多检查一次官网。发现新版时先完成原任务，再在回答末尾提醒；紧接提醒回复1才升级。更新器检查版本、字节数、SHA-256和ZIP路径，升级前备份，替换失败回滚。没有Python或检查失败时仍可继续使用写作规则；定时任务跳过检查。更新器不会后台推送，也不自动更新其他Skill。

## 个人资料

不填个人档案也能使用。背书模板为空，个人经历只从使用者提供的真实资料中获取。原有本机私有完整标本和研究历史可放在用户自己的私有库，公开发行包不包含它们。安装和升级不更改目录外资料，保留旧安装中的个人背书档案。

## 授权与来源

程序代码MIT；本项目原创规则与说明CC BY-NC 4.0。具体边界见CONTENT-LICENSE.md。第三方作品不在本项目授权范围内；用户自己的稿件和作品不因此受本项目许可限制。公开包只含结构观察，不转载第三方完整开头；启发来源见开头skill/references/sources.md。

## 本地验证与构建

Python 3.9+：

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/build_release.py
```

## 联系敏敏

使用中有问题，或想交流新想法？欢迎微信联系。微信号：**min11538**。

![敏敏的微信二维码](contact/wechat-min11538.jpg)

安装页：https://tools.minmin11538.cn/opening/#contact-minmin

联系图片的使用范围见[ASSET-LICENSE.md](ASSET-LICENSE.md)。
