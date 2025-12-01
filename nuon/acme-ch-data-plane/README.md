{{ $region := .nuon.cloud_account.aws.region }}

<center>
  <img src="https://mintlify.s3-us-west-1.amazonaws.com/nuoninc/logo/dark.svg"/>
  <h1>
    ClickHouse Data Plane
  </h1>
  <small>
{{ if .nuon.install_stack.outputs }}
AWS | {{ dig "account_id" "000000000000" .nuon.install_stack.outputs }} | {{ dig "region" "xx-vvvv-00" .nuon.install_stack.outputs }} | {{ dig "vpc_id" "vpc-000000" .nuon.install_stack.outputs }}
{{ else }}
AWS | 000000000000 | xx-vvvv-00 | vpc-000000
{{ end }}
  </small>
</center>

<center>
The data-plane for a BYOC A.C.M.E. ClickHouse install.
</center>
