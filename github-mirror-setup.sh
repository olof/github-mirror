#!/bin/sh

die() {
	echo Error: "$@" >&2
	exit 1
}

usage() {
	echo "$0 <owner> <repo> <mailing list> [<from>]"
	exit 0
}

words() {
	echo $#
}

gen_clone_url() {
	local repo="$1" owner="$2"
	printf $GITHUB_CLONE_URL "$owner" "$repo" ||
		die 'Invalid GITHUB_CLONE_URL template'
}

. /etc/github-mirror.conf

owner=$1 repo=$2 ml=$3 from=$4

[ "$owner" ] && [ "$repo" ] && [ "$ml" ] || usage
case $owner in
	--help|-h) usage ;;
esac

[    "$GIT_HOOK" ] || die "GIT_HOOK not set in configuration"
[ -r "$GIT_HOOK" ] || die "Could not read $GIT_HOOK"
[ $(expr substr "$GIT_HOOK" 1 1) = / ] ||
	die 'GIT_HOOK must be an absolute path'

[ "$GITHUB_CLONE_URL" ] || die "GITHUB_CLONE_URL template is not specified"

[ $(words "$owner") -eq 1 ] || die 'owner has to be a single word'
[ $(words "$repo" ) -eq 1 ] || die 'repo has to be a single word'
[ $(words "$ml"   ) -eq 1 ] || die 'mailing list has to be a single word'

cd "$REPO_PATH"   || die "Could not cd to $REPO_PATH"
mkdir -p "$owner" || die "Could not create $owner dir in $REPO_PATH"
cd "$owner"       || die "Could not cd to $owner dir in $REPO_PATH"

git clone --bare $(gen_clone_url "$repo" "$owner") ||
	die "Failed to clone $(gen_clone_url "$repo" "$owner")"
cd "$repo.git" || die "Could not cd to $owner/$repo.git"

git config hooks.mailinglist "$ml"
git config hooks.showrev 'git show -C %s; echo'
[ -z "$from" ] || git config hooks.envelopesender "$from"

rm hooks/*
cat << EOF > hooks/post-receive
#!/bin/sh
. $GIT_HOOK
EOF
chmod +x hooks/post-receive

echo $owner/$repo > description

