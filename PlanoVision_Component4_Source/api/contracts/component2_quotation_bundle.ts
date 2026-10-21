// Proposed integration contract; Component 2 has not yet confirmed/connected it.
import type {Quote} from '../../frontend/src/api';
export type Component2QuotationBundle={contract_version:'component2.quotation_bundle.v1';bundle_id:string;supplier_id:string;issued_on:string;event_type:'Wedding'|'Corporate';event_date:string;quotations:(Omit<Quote,'source_kind'>&{currency:'LKR'})[]};
// Verification/approval/outcome/prediction fields are deliberately not accepted.
