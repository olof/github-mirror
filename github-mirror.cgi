#!/bin/sh
# Copyright 2012, Olof Johansson <olof@ethup.se>
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty
# provided the copyright notice are preserved. This file is
# offered as-is, without any warranty.

# Abstract
# ========
# This is a CGI script used for mirroring a github hosted repo.
# It's intended to be hosted somewhere Github can make requests
# against it as a repository service hook. The usecase in mind is
# to be able to run local post-receive hooks for sending commit
# mails with diffs (something github unfortunately doesn't
# support currently).

TMP=

log() {
	echo "$@" 1>&2
}

gen_clone_url() {
	local repo="$1" owner="$2"
	printf $GITHUB_CLONE_URL "$owner" "$repo"
}

tmpclone() {
	local repo="$1" owner="$2" repodir="$PWD/$owner/$repo.git"
	TMP=$(mktemp -d /tmp/github-mirror-XXXXXX)
	[ "$TMP" ] || render 500 'Could not create temporary directory'
	trap cleanup EXIT

	(
		cd $TMP &&
		git clone "$(gen_clone_url $repo $owner)" . >/dev/null &&
		git remote add local $repodir &&
		git push local --all >/dev/null
	) || render 500 "Could not clone $owner/$repo"
}

cleanup() {
	[ "$TMP" ] && [ -d "$TMP" ] && rm -rf "$TMP"
}

render() {
	local status="$1" msg="$2" status_msg=

	case $status in
		200)
			status_msg="OK"
		;;
		400)
			status_msg="Bad Request"
		;;
		403)
			status_msg="Unauthorized"
		;;
		404)
			status_msg="Not Found"
		;;
		500)
			[ "$msg" ] && log "500: $msg"
			status_msg="Internal Server Error"
		;;
		*)
			log "Status $status isn't supported, changing it to 500"
			[ "$msg" ] && log "Message was: $msg"
			status=500
			status_msg="Internal Server Error"
		;;
	esac

	[ "$msg" ] || msg=$status_msg

	printf "Status: $status $status_msg\r\n"
	printf "Content-Type: text/plain; charset=UTF-8\r\n"
	printf "\r\n"

	echo "$msg"
	exit 0
}

value_if_key() {
	[ "$1" = "$2" ] && echo $3
}

repo_exists() {
	local repo="$1" owner="$2"
	[ -d "$owner/$repo.git" ]
}

verify_repo() {
	local repo="$1" owner="$2"

	repo_exists "$repo" "$owner" || render 404
}

repo() {
	local repo="$1" owner="$2"

	verify_repo "$repo" "$owner"
	tmpclone "$repo" "$owner"
	render 200
}

from_qstring() {
	local key="$1"

	(
		IFS='&'
		for param in $QUERY_STRING; do (
			IFS==
			value_if_key $key $param
		) done
	)
}

. /etc/github-mirror.conf || render 500 "Could not load config file"

[ "$REPO_PATH" ] || render 500 "No repo path specified"
cd $REPO_PATH || render 500 "Could not cd to REPO_PATH ($REPO_PATH)"

repo=$(from_qstring repo)
owner=$(from_qstring owner)

[ "$repo"  ] || render 400 'No repo supplied in query string'
[ "$owner" ] || render 400 'No owner supplied in query string'

repo "$repo" "$owner"

